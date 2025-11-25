"""
Counterfactual Fairness Analyzer for TrustChain.

Tests fairness by modifying protected attributes and checking if decisions
change. If swapping "Jamal" to "Brad" flips a rejection to approval,
that's measurable discrimination.

Usage:
    analyzer = CounterfactualFairnessAnalyzer()
    result = await analyzer.analyze_async(
        strategy_result=original_result,
        input_data=application_data,
        context={},
        trustchain_instance=tc
    )

Built with care by Kareem & Claude
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from enum import Enum

from core.base import BaseAnalyzer
from core.result import AnalysisResult, DecisionOutcome
from .counterfactual_generator import (
    CounterfactualGenerator,
    Counterfactual,
    ProtectedAttribute
)

if TYPE_CHECKING:
    from core.result import StrategyResult

logger = logging.getLogger(__name__)


class BiasStrength(str, Enum):
    """Strength of detected bias."""
    NONE = "none"           # No bias detected
    WEAK = "weak"           # Minor confidence changes
    MODERATE = "moderate"   # Clear decision flips
    STRONG = "strong"       # Consistent flips with high confidence


@dataclass
class CounterfactualResult:
    """Result of running a single counterfactual."""

    counterfactual: Counterfactual

    # Original decision
    original_decision: DecisionOutcome
    original_confidence: float

    # Counterfactual decision
    counterfactual_decision: DecisionOutcome
    counterfactual_confidence: float

    # Analysis
    decision_changed: bool
    confidence_delta: float
    bias_detected: bool
    bias_strength: BiasStrength

    # Explanation
    explanation: str


@dataclass
class CounterfactualFairnessResult:
    """Complete counterfactual fairness analysis."""

    # Overall fairness score (0.0 = total bias, 1.0 = no bias)
    fairness_score: float

    # Individual counterfactual results
    counterfactual_results: List[CounterfactualResult] = field(default_factory=list)

    # Summary
    biases_detected: List[ProtectedAttribute] = field(default_factory=list)
    bias_strength: BiasStrength = BiasStrength.NONE

    # Detailed breakdown
    total_counterfactuals: int = 0
    flipped_decisions: int = 0

    # Explanation
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class CounterfactualFairnessAnalyzer(BaseAnalyzer):
    """
    Analyzer that tests counterfactual fairness.

    Generates counterfactual versions of input by modifying protected
    attributes, re-runs decisions, and checks if outcomes change.

    This analyzer is EXPENSIVE - it requires multiple TrustChain evaluations.
    Use sparingly for high-stakes decisions or auditing.

    Usage:
        analyzer = CounterfactualFairnessAnalyzer()
        result = await analyzer.analyze_async(
            strategy_result=original_result,
            input_data=application_data,
            context={},
            trustchain_instance=tc
        )
    """

    name = "counterfactual_fairness"
    description = "Tests if decisions change when protected attributes are modified"
    version = "1.0.0"
    blocking = True  # Bias detection blocks automated decisions

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.generator = CounterfactualGenerator(config)

        # Thresholds
        self.flip_threshold = config.get("flip_threshold", 0.15) if config else 0.15
        self.fairness_threshold = config.get("fairness_threshold", 0.7) if config else 0.7

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate analyzer configuration."""
        if "flip_threshold" in config:
            if not 0 <= config["flip_threshold"] <= 1:
                raise ValueError("flip_threshold must be between 0 and 1")
        if "fairness_threshold" in config:
            if not 0 <= config["fairness_threshold"] <= 1:
                raise ValueError("fairness_threshold must be between 0 and 1")
        return True

    def analyze(
        self,
        strategy_result: "StrategyResult",
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Synchronous analysis - returns warning that async is needed.

        Counterfactual testing requires async for TrustChain re-runs.
        """
        return AnalysisResult(
            analyzer_name=self.name,
            passed=True,
            flags=[],
            warnings=[
                "Counterfactual fairness testing requires async execution. "
                "Use analyze_async() with trustchain_instance parameter."
            ],
            details={},
            recommendation="Call analyze_async() for full counterfactual testing"
        )

    async def analyze_async(
        self,
        strategy_result: "StrategyResult",
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        trustchain_instance: Any = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Run counterfactual fairness analysis.

        Args:
            strategy_result: Result from original TrustChain decision
            input_data: Original input data
            context: Policy context
            trustchain_instance: TrustChain instance to re-run decisions
        """
        if trustchain_instance is None:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No TrustChain instance provided - skipping counterfactual testing"],
                details={},
                recommendation="Provide trustchain_instance for counterfactual testing"
            )

        # Generate all counterfactuals
        counterfactuals = self.generator.generate_all(input_data)

        if not counterfactuals:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No counterfactuals could be generated for this input"],
                details={"reason": "Input lacks protected attributes to test"},
                recommendation="Unable to perform counterfactual fairness testing - no testable attributes found"
            )

        logger.info(f"Running {len(counterfactuals)} counterfactual tests")

        # Run each counterfactual through TrustChain
        cf_results = []
        for cf in counterfactuals:
            try:
                cf_result = await self._run_counterfactual(
                    cf,
                    input_data,
                    strategy_result,
                    trustchain_instance
                )
                cf_results.append(cf_result)
            except Exception as e:
                logger.warning(f"Failed to run counterfactual {cf.counterfactual_id}: {e}")

        if not cf_results:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["All counterfactual tests failed to execute"],
                details={},
                recommendation="Check TrustChain configuration for counterfactual support"
            )

        # Analyze results
        analysis = self._analyze_counterfactual_results(cf_results, strategy_result)

        # Determine pass/fail
        passed = analysis.fairness_score >= self.fairness_threshold

        # Generate flags
        flags = []
        if not passed:
            for bias_attr in analysis.biases_detected:
                flags.append(
                    f"Counterfactual bias detected: {bias_attr.value} "
                    f"(strength: {analysis.bias_strength.value})"
                )

        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=[],
            details={
                "fairness_score": analysis.fairness_score,
                "biases_detected": [b.value for b in analysis.biases_detected],
                "bias_strength": analysis.bias_strength.value,
                "total_counterfactuals": analysis.total_counterfactuals,
                "flipped_decisions": analysis.flipped_decisions,
                "summary": analysis.summary,
                "recommendations": analysis.recommendations,
                "counterfactual_results": [
                    {
                        "id": cf_result.counterfactual.counterfactual_id,
                        "modification": cf_result.counterfactual.modification_method,
                        "attribute": cf_result.counterfactual.modifications[0].attribute.value if cf_result.counterfactual.modifications else "unknown",
                        "original_value": cf_result.counterfactual.modifications[0].original_value if cf_result.counterfactual.modifications else None,
                        "modified_value": cf_result.counterfactual.modifications[0].modified_value if cf_result.counterfactual.modifications else None,
                        "original_decision": cf_result.original_decision.value,
                        "counterfactual_decision": cf_result.counterfactual_decision.value,
                        "decision_changed": cf_result.decision_changed,
                        "confidence_delta": round(cf_result.confidence_delta, 3),
                        "bias_detected": cf_result.bias_detected,
                        "bias_strength": cf_result.bias_strength.value,
                        "explanation": cf_result.explanation
                    }
                    for cf_result in cf_results
                ]
            },
            recommendation=analysis.summary
        )

    async def _run_counterfactual(
        self,
        counterfactual: Counterfactual,
        original_input: Dict[str, Any],
        original_result: "StrategyResult",
        trustchain: Any
    ) -> CounterfactualResult:
        """
        Run a single counterfactual through TrustChain.

        Returns comparison with original decision.
        """
        # Re-run TrustChain with modified input
        # Use skip_analyzers=True to avoid infinite recursion
        cf_decision_result = await trustchain.evaluate(
            case_id=f"cf_{counterfactual.counterfactual_id}",
            input_data=counterfactual.modified_input,
            skip_analyzers=True  # Don't run other analyzers
        )

        # Compare decisions
        original_decision = original_result.decision
        original_confidence = original_result.confidence

        cf_decision = cf_decision_result.final_decision
        cf_confidence = cf_decision_result.overall_confidence

        decision_changed = original_decision != cf_decision
        confidence_delta = abs(cf_confidence - original_confidence)

        # Determine if this indicates bias
        bias_detected = decision_changed or confidence_delta > self.flip_threshold

        # Assess strength
        if not bias_detected:
            bias_strength = BiasStrength.NONE
        elif decision_changed and confidence_delta > 0.2:
            bias_strength = BiasStrength.STRONG
        elif decision_changed:
            bias_strength = BiasStrength.MODERATE
        else:
            bias_strength = BiasStrength.WEAK

        # Generate explanation
        explanation = self._generate_explanation(
            counterfactual,
            original_decision,
            original_confidence,
            cf_decision,
            cf_confidence,
            bias_detected
        )

        return CounterfactualResult(
            counterfactual=counterfactual,
            original_decision=original_decision,
            original_confidence=original_confidence,
            counterfactual_decision=cf_decision,
            counterfactual_confidence=cf_confidence,
            decision_changed=decision_changed,
            confidence_delta=confidence_delta,
            bias_detected=bias_detected,
            bias_strength=bias_strength,
            explanation=explanation
        )

    def _analyze_counterfactual_results(
        self,
        cf_results: List[CounterfactualResult],
        original_result: "StrategyResult"
    ) -> CounterfactualFairnessResult:
        """
        Aggregate counterfactual results into overall fairness assessment.
        """
        total = len(cf_results)
        flipped = sum(1 for r in cf_results if r.decision_changed)
        biased = [r for r in cf_results if r.bias_detected]

        # Calculate fairness score
        # 1.0 = no flips, 0.0 = all flipped
        fairness_score = 1.0 - (flipped / total) if total > 0 else 1.0

        # Identify which attributes caused bias
        biases_detected = []
        for result in biased:
            for mod in result.counterfactual.modifications:
                if mod.attribute not in biases_detected:
                    biases_detected.append(mod.attribute)

        # Determine overall bias strength
        if not biased:
            overall_strength = BiasStrength.NONE
        else:
            strengths = [r.bias_strength for r in biased]
            if BiasStrength.STRONG in strengths:
                overall_strength = BiasStrength.STRONG
            elif BiasStrength.MODERATE in strengths:
                overall_strength = BiasStrength.MODERATE
            else:
                overall_strength = BiasStrength.WEAK

        # Generate summary
        summary = self._generate_summary(
            fairness_score,
            flipped,
            total,
            biases_detected,
            overall_strength
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(biases_detected, cf_results)

        return CounterfactualFairnessResult(
            fairness_score=fairness_score,
            counterfactual_results=cf_results,
            biases_detected=biases_detected,
            bias_strength=overall_strength,
            total_counterfactuals=total,
            flipped_decisions=flipped,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_explanation(
        self,
        cf: Counterfactual,
        orig_decision: DecisionOutcome,
        orig_conf: float,
        cf_decision: DecisionOutcome,
        cf_conf: float,
        bias_detected: bool
    ) -> str:
        """Generate explanation for a single counterfactual result."""

        mod = cf.modifications[0] if cf.modifications else None

        if not mod:
            return "No modification to analyze"

        if not bias_detected:
            return f"Changing {mod.attribute.value} did not affect the decision. No bias detected."

        if orig_decision != cf_decision:
            return (
                f"BIAS DETECTED: Changing {mod.attribute.value} from "
                f"'{mod.original_value}' to '{mod.modified_value}' flipped the decision from "
                f"{orig_decision.value} ({orig_conf:.2f}) to {cf_decision.value} ({cf_conf:.2f}). "
                f"This suggests discrimination based on {mod.attribute.value}."
            )
        else:
            return (
                f"Moderate bias: Changing {mod.attribute.value} significantly altered confidence "
                f"({orig_conf:.2f} -> {cf_conf:.2f}) without flipping the decision."
            )

    def _generate_summary(
        self,
        fairness_score: float,
        flipped: int,
        total: int,
        biases: List[ProtectedAttribute],
        strength: BiasStrength
    ) -> str:
        """Generate overall summary."""

        if fairness_score >= 0.9:
            return (
                f"HIGH FAIRNESS: Decisions were consistent across {total} counterfactual tests. "
                f"No significant bias detected based on protected attributes."
            )

        if fairness_score >= 0.7:
            return (
                f"MODERATE FAIRNESS: {flipped}/{total} counterfactuals changed decisions. "
                f"Minor inconsistencies detected but may be within acceptable bounds."
            )

        bias_list = ", ".join([b.value for b in biases])
        return (
            f"LOW FAIRNESS: {flipped}/{total} counterfactuals changed decisions. "
            f"{strength.value.upper()} bias detected in: {bias_list}. "
            f"The model's decisions are significantly influenced by protected attributes."
        )

    def _generate_recommendations(
        self,
        biases: List[ProtectedAttribute],
        results: List[CounterfactualResult]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if not biases:
            recommendations.append(
                "No counterfactual bias detected. Continue monitoring with periodic testing."
            )
            return recommendations

        for bias_attr in biases:
            # Find strongest example
            relevant = [
                r for r in results
                if any(m.attribute == bias_attr for m in r.counterfactual.modifications)
                and r.bias_detected
            ]

            if relevant:
                example = max(relevant, key=lambda r: r.confidence_delta)
                mod = example.counterfactual.modifications[0]

                recommendations.append(
                    f"Address {bias_attr.value} bias: Decisions changed when modifying "
                    f"'{mod.original_value}' to '{mod.modified_value}'. "
                    f"Review prompts and training data for implicit associations."
                )

        recommendations.append(
            "Consider using fairness constraints in evaluation criteria."
        )

        recommendations.append(
            "Implement blind review where protected attributes are masked before evaluation."
        )

        return recommendations
