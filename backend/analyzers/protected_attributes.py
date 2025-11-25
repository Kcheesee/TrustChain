"""
Protected Attributes Analyzer for TrustChain.

Detects mentions of protected attributes in AI reasoning that could
indicate discriminatory decision-making. This is a critical safety
component for high-stakes government decisions.

Refactored from the original bias_detection.py to fit the plugin architecture.

Built with care by Kareem & Claude
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from core.base import BaseAnalyzer
from core.registry import register_component
from core.result import StrategyResult, AnalysisResult

logger = logging.getLogger(__name__)


class ProtectedAttribute(str, Enum):
    """
    Protected attributes under civil rights law.

    These attributes should NEVER be the basis for government decisions.
    If detected in reasoning, flag immediately for human review.
    """
    RACE = "race"
    ETHNICITY = "ethnicity"
    NATIONAL_ORIGIN = "national_origin"
    GENDER = "gender"
    AGE = "age"
    RELIGION = "religion"
    DISABILITY = "disability"
    SEXUAL_ORIENTATION = "sexual_orientation"
    PREGNANCY = "pregnancy"
    VETERAN_STATUS = "veteran_status"


class SafetyTrigger(str, Enum):
    """Conditions that require human review regardless of consensus."""
    PROTECTED_ATTRIBUTE_MENTIONED = "protected_attribute_mentioned"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_STAKES_DECISION = "high_stakes_decision"
    CONFLICTING_REASONING = "conflicting_reasoning"
    INSUFFICIENT_DATA = "insufficient_data"
    DEPORTATION_RISK = "deportation_risk"
    BENEFIT_TERMINATION = "benefit_termination"


# Keywords that indicate protected attributes
PROTECTED_KEYWORDS: Dict[ProtectedAttribute, List[str]] = {
    ProtectedAttribute.RACE: [
        "race", "racial", "black", "white", "asian", "hispanic",
        "latino", "latina", "african american", "caucasian"
    ],
    ProtectedAttribute.ETHNICITY: [
        "ethnicity", "ethnic", "minority", "cultural background"
    ],
    ProtectedAttribute.NATIONAL_ORIGIN: [
        "country of origin", "nationality", "immigrant", "foreign",
        "native-born", "birthplace", "citizen", "citizenship"
    ],
    ProtectedAttribute.GENDER: [
        "gender", "male", "female", "man", "woman", "sex",
        "transgender", "non-binary"
    ],
    ProtectedAttribute.AGE: [
        "age", "elderly", "senior", "young", "older worker",
        "retirement age", "generational"
    ],
    ProtectedAttribute.RELIGION: [
        "religion", "religious", "christian", "muslim", "jewish",
        "hindu", "buddhist", "atheist", "faith"
    ],
    ProtectedAttribute.DISABILITY: [
        "disability", "disabled", "handicap", "impairment",
        "medical condition", "accommodation"
    ],
    ProtectedAttribute.SEXUAL_ORIENTATION: [
        "sexual orientation", "gay", "lesbian", "bisexual",
        "lgbtq", "homosexual", "heterosexual"
    ],
    ProtectedAttribute.PREGNANCY: [
        "pregnancy", "pregnant", "maternity", "childbirth",
        "expecting", "parental leave"
    ],
    ProtectedAttribute.VETERAN_STATUS: [
        "veteran", "military service", "armed forces", "discharge"
    ]
}

# High-stakes decision types that always require extra scrutiny
HIGH_STAKES_DECISION_TYPES = [
    "immigration_deportation",
    "asylum_decision",
    "benefit_termination",
    "housing_denial",
    "loan_denial",
    "employment_termination"
]


@register_component
class ProtectedAttributesAnalyzer(BaseAnalyzer):
    """
    Analyzer that detects mentions of protected attributes in AI reasoning.

    This is a critical safety component. It scans model reasoning for
    keywords that might indicate the decision was influenced by
    protected characteristics like race, gender, age, etc.

    Configuration options:
        strict_mode: If True, flag ANY mention (default True)
        confidence_threshold: Below this, flag as low confidence (default 0.7)
        high_stakes_types: List of decision types requiring extra scrutiny

    Example:
        analyzer = ProtectedAttributesAnalyzer(config={
            "strict_mode": True,
            "confidence_threshold": 0.7
        })
        result = analyzer.analyze(strategy_result, input_data, context)
    """

    name = "protected_attributes"
    description = "Detect protected attribute mentions that may indicate bias"
    version = "1.0.0"
    blocking = True  # Failures require human review

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the protected attributes analyzer."""
        super().__init__(config)

        self.strict_mode = self.config.get("strict_mode", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.high_stakes_types = self.config.get(
            "high_stakes_types",
            HIGH_STAKES_DECISION_TYPES
        )

        logger.info(
            f"ProtectedAttributesAnalyzer initialized: "
            f"strict_mode={self.strict_mode}, "
            f"confidence_threshold={self.confidence_threshold:.0%}"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate analyzer configuration."""
        if "confidence_threshold" in config:
            threshold = config["confidence_threshold"]
            if not 0 <= threshold <= 1:
                raise ValueError("confidence_threshold must be between 0 and 1")
        return True

    def adjust_sensitivity(self, multiplier: float) -> None:
        """
        Adjust analyzer sensitivity based on learned feedback.

        This is the Phase 3 learning hook - adjusts confidence threshold
        based on false positive/negative rates from human feedback.

        Higher multiplier = more strict (lower threshold triggers more flags)
        Lower multiplier = less strict (higher threshold, fewer flags)

        Args:
            multiplier: Sensitivity multiplier (>1 = stricter, <1 = more lenient)
        """
        old_threshold = self.confidence_threshold

        # Inverse relationship: higher multiplier = lower threshold = more flags
        # We clamp between 0.5 and 0.95 to prevent extremes
        new_threshold = max(0.5, min(0.95, self.confidence_threshold / multiplier))
        self.confidence_threshold = new_threshold

        if abs(old_threshold - new_threshold) > 0.01:
            logger.info(
                f"ProtectedAttributesAnalyzer threshold adjusted: "
                f"{old_threshold:.2f} -> {new_threshold:.2f} (multiplier: {multiplier:.2f})"
            )

        # Also adjust strict_mode based on multiplier
        if multiplier > 1.3 and not self.strict_mode:
            self.strict_mode = True
            logger.info("ProtectedAttributesAnalyzer: strict_mode enabled due to high multiplier")
        elif multiplier < 0.7 and self.strict_mode:
            self.strict_mode = False
            logger.info("ProtectedAttributesAnalyzer: strict_mode disabled due to low multiplier")

    def get_sensitivity_settings(self) -> Dict[str, Any]:
        """Get current sensitivity settings (for inspection/debugging)."""
        return {
            "confidence_threshold": self.confidence_threshold,
            "strict_mode": self.strict_mode,
        }

    def analyze(
        self,
        strategy_result: StrategyResult,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Analyze strategy result for protected attribute mentions.

        Args:
            strategy_result: Output from the evaluation strategy
            input_data: Original case/application data
            context: Policy context including decision_type

        Returns:
            AnalysisResult with bias detection findings
        """
        logger.info("Running protected attributes analysis...")

        detected_attributes: Set[str] = set()
        safety_triggers: List[SafetyTrigger] = []
        flags: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        decision_type = context.get("decision_type", "general")

        # CHECK 1: Scan reasoning for protected attributes
        all_reasoning = self._collect_reasoning(strategy_result)

        for attr, keywords in PROTECTED_KEYWORDS.items():
            for keyword in keywords:
                if keyword in all_reasoning.lower():
                    detected_attributes.add(attr.value)
                    safety_triggers.append(SafetyTrigger.PROTECTED_ATTRIBUTE_MENTIONED)
                    flags.append(
                        f"Protected attribute '{attr.value}' detected (keyword: '{keyword}')"
                    )
                    logger.warning(f"Protected attribute detected: {attr.value}")

        # CHECK 2: Low confidence
        if strategy_result.confidence < self.confidence_threshold:
            safety_triggers.append(SafetyTrigger.LOW_CONFIDENCE)
            warnings.append(
                f"Low confidence ({strategy_result.confidence:.0%}) "
                f"below threshold ({self.confidence_threshold:.0%})"
            )

        # CHECK 3: High-stakes decision types
        if decision_type in self.high_stakes_types:
            safety_triggers.append(SafetyTrigger.HIGH_STAKES_DECISION)
            warnings.append(f"High-stakes decision type: {decision_type}")

        # CHECK 4: Conflicting reasoning (high variance despite agreement)
        if strategy_result.agreement_level == 1.0:  # All agree
            # Check if model decisions have high confidence variance
            if strategy_result.model_decisions:
                confidences = [
                    d.get("confidence", 0.5) for d in strategy_result.model_decisions
                ]
                if len(confidences) > 1:
                    mean_conf = sum(confidences) / len(confidences)
                    variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
                    if variance > 0.1:
                        safety_triggers.append(SafetyTrigger.CONFLICTING_REASONING)
                        warnings.append(
                            f"High confidence variance ({variance:.4f}) despite consensus"
                        )

        # CHECK 5: Insufficient data (check required fields)
        missing_fields = self._check_required_fields(decision_type, input_data)
        if missing_fields:
            safety_triggers.append(SafetyTrigger.INSUFFICIENT_DATA)
            warnings.append(f"Missing required fields: {', '.join(missing_fields)}")

        # CHECK 6: Critical decision types
        if decision_type in ["immigration_deportation", "visa_denial"]:
            safety_triggers.append(SafetyTrigger.DEPORTATION_RISK)
            flags.append("DEPORTATION RISK - Mandatory human review required")

        if decision_type == "benefit_termination":
            safety_triggers.append(SafetyTrigger.BENEFIT_TERMINATION)
            flags.append("BENEFIT TERMINATION - Mandatory human review required")

        # Determine if analysis passed
        passed = len(detected_attributes) == 0 and len(flags) == 0

        # Generate recommendation
        recommendation = self._generate_recommendation(
            detected_attributes, safety_triggers, strategy_result.confidence
        )

        # Build details
        details = {
            "safety_triggers": [t.value for t in safety_triggers],
            "keyword_matches": list(detected_attributes),
            "decision_type": decision_type,
            "confidence_checked": strategy_result.confidence,
        }

        result = AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details=details,
            recommendation=recommendation,
            detected_attributes=list(detected_attributes),
            detected_proxies=[],  # Proxy detection is a separate analyzer
        )

        if not passed:
            logger.warning(
                f"Analysis FAILED: {len(detected_attributes)} protected attributes, "
                f"{len(safety_triggers)} safety triggers"
            )
        else:
            logger.info("Analysis passed: No protected attribute mentions detected")

        return result

    def _collect_reasoning(self, strategy_result: StrategyResult) -> str:
        """Collect all reasoning text from strategy result."""
        reasoning_parts = [strategy_result.reasoning]

        # Add reasoning from individual model decisions
        for decision in strategy_result.model_decisions:
            if isinstance(decision, dict):
                reasoning_parts.append(decision.get("reasoning", ""))
            elif hasattr(decision, "reasoning"):
                reasoning_parts.append(decision.reasoning)

        # Add dissenting views
        reasoning_parts.extend(strategy_result.dissenting_views)

        return " ".join(reasoning_parts)

    def _check_required_fields(
        self,
        decision_type: str,
        input_data: Dict[str, Any]
    ) -> List[str]:
        """Check for missing required fields based on decision type."""
        field_requirements = {
            "unemployment_benefits": [
                "employment_duration_months",
                "termination_reason",
                "available_for_work"
            ],
            "immigration_deportation": [
                "visa_status",
                "entry_date",
                "criminal_record",
                "family_ties"
            ],
            "loan_approval": [
                "credit_score",
                "income",
                "debt_to_income_ratio"
            ]
        }

        required = field_requirements.get(decision_type, [])
        return [f for f in required if f not in input_data]

    def _generate_recommendation(
        self,
        detected_attributes: Set[str],
        safety_triggers: List[SafetyTrigger],
        confidence: float
    ) -> str:
        """Generate human-readable safety recommendation."""
        if not detected_attributes and not safety_triggers:
            return "No bias indicators detected. Decision may proceed if consensus is adequate."

        recommendations = []

        if detected_attributes:
            recommendations.append(
                f"CRITICAL: Protected attributes mentioned ({', '.join(detected_attributes)}). "
                f"Verify decision is not based on discriminatory factors."
            )

        if SafetyTrigger.LOW_CONFIDENCE in safety_triggers:
            recommendations.append(
                f"Models show low confidence ({confidence:.0%}). "
                f"Review case for missing information or ambiguity."
            )

        if SafetyTrigger.HIGH_STAKES_DECISION in safety_triggers:
            recommendations.append(
                "High-stakes decision with significant impact on applicant. "
                "Ensure thorough review of all factors."
            )

        if SafetyTrigger.DEPORTATION_RISK in safety_triggers:
            recommendations.append(
                "DEPORTATION RISK: This decision could result in removal from country. "
                "Mandatory legal review and applicant notification required."
            )

        if SafetyTrigger.BENEFIT_TERMINATION in safety_triggers:
            recommendations.append(
                "BENEFIT TERMINATION: This will end critical support for the applicant. "
                "Ensure all alternatives have been considered."
            )

        return " ".join(recommendations)
