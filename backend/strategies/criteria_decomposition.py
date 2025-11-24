"""
Criteria Decomposition Strategy for TrustChain.

This strategy breaks down decisions into individual criteria, scores each
one separately, then aggregates for a final decision. Works with single
or multiple models.

Example: For a hiring decision:
- Experience requirement: 0.9 (meets 5+ years)
- Skills requirement: 0.7 (has 4/5 required skills)
- Education requirement: 0.85 (has relevant degree)
- Final: APPROVE with 0.82 confidence

This approach provides:
- Granular explainability (which criteria passed/failed)
- Better calibration (scoring vs binary decision)
- Audit-friendly output (clear criteria breakdown)

Built with care by Kareem & Claude
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.base import BaseStrategy
from core.registry import register_component
from core.result import StrategyResult, DecisionOutcome

logger = logging.getLogger(__name__)


@register_component
class CriteriaDecompositionStrategy(BaseStrategy):
    """
    Criteria decomposition evaluation strategy.

    Breaks decisions into individual criteria, evaluates each one,
    then aggregates scores for a final decision. Works with a single
    model (no multi-model requirement).

    Configuration options:
        criteria: List of criteria to evaluate (required)
        weights: Optional weights for each criterion (default: equal)
        passing_threshold: Score needed to pass (default: 0.6)
        aggregation: How to combine scores - 'weighted_avg', 'min', 'all_pass' (default: weighted_avg)
        require_all_critical: If True, all criteria marked critical must pass

    Example:
        strategy = CriteriaDecompositionStrategy(config={
            "criteria": [
                {"name": "experience", "description": "5+ years relevant experience", "weight": 1.0, "critical": False},
                {"name": "skills", "description": "Required technical skills", "weight": 1.2, "critical": True},
                {"name": "education", "description": "Relevant degree or equivalent", "weight": 0.8},
            ],
            "passing_threshold": 0.6,
            "aggregation": "weighted_avg"
        })
    """

    name = "criteria_decomposition"
    description = "Break decision into scored criteria for granular explainability"
    version = "1.0.0"
    requires_multiple_providers = False
    min_providers = 1

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize criteria decomposition strategy."""
        super().__init__(config)

        self.criteria = self.config.get("criteria", [])
        self.weights = self.config.get("weights", {})
        self.passing_threshold = self.config.get("passing_threshold", 0.6)
        self.aggregation = self.config.get("aggregation", "weighted_avg")
        self.require_all_critical = self.config.get("require_all_critical", True)

        logger.info(
            f"CriteriaDecompositionStrategy initialized: "
            f"{len(self.criteria)} criteria, threshold={self.passing_threshold}"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration."""
        if "criteria" in config and not config["criteria"]:
            raise ValueError("criteria list cannot be empty")

        if "passing_threshold" in config:
            threshold = config["passing_threshold"]
            if not 0 <= threshold <= 1:
                raise ValueError("passing_threshold must be between 0 and 1")

        valid_aggregations = ["weighted_avg", "min", "all_pass"]
        if "aggregation" in config and config["aggregation"] not in valid_aggregations:
            raise ValueError(f"aggregation must be one of: {valid_aggregations}")

        return True

    async def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        providers: List[Any]
    ) -> StrategyResult:
        """
        Execute criteria decomposition evaluation.

        Args:
            input_data: Case data to evaluate
            context: Policy context with criteria definitions
            providers: Available LLM providers (uses first one)

        Returns:
            StrategyResult with criteria scores and aggregated decision
        """
        start_time = datetime.now()

        if not providers:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="No LLM providers available",
            )

        # Use first available provider
        provider = providers[0]

        # Get criteria from config or context
        criteria = self.criteria or context.get("criteria", [])
        if not criteria:
            # Generate default criteria from decision type
            criteria = self._generate_default_criteria(context.get("decision_type", "general"))

        logger.info(f"Evaluating {len(criteria)} criteria...")

        # Evaluate each criterion
        criteria_scores = {}
        criteria_details = []

        for criterion in criteria:
            crit_name = criterion.get("name", criterion) if isinstance(criterion, dict) else criterion
            crit_desc = criterion.get("description", crit_name) if isinstance(criterion, dict) else crit_name
            crit_weight = criterion.get("weight", 1.0) if isinstance(criterion, dict) else 1.0
            crit_critical = criterion.get("critical", False) if isinstance(criterion, dict) else False

            score, reasoning = await self._evaluate_criterion(
                provider, input_data, context, crit_name, crit_desc
            )

            criteria_scores[crit_name] = {
                "score": score,
                "weight": crit_weight,
                "critical": crit_critical,
                "passed": score >= self.passing_threshold,
                "reasoning": reasoning,
            }

            criteria_details.append({
                "criterion": crit_name,
                "description": crit_desc,
                "score": score,
                "passed": score >= self.passing_threshold,
                "reasoning": reasoning,
            })

            logger.debug(f"  {crit_name}: {score:.2f} ({'PASS' if score >= self.passing_threshold else 'FAIL'})")

        # Aggregate scores
        final_score, decision = self._aggregate_scores(criteria_scores)

        # Build reasoning
        reasoning = self._build_reasoning(criteria_scores, final_score, decision)

        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        result = StrategyResult(
            strategy_name=self.name,
            decision=decision,
            confidence=final_score,
            reasoning=reasoning,
            criteria_scores=criteria_scores,
            model_decisions=[{
                "provider": provider.__class__.__name__,
                "decision": decision.value,
                "confidence": final_score,
                "criteria_breakdown": criteria_details,
            }],
            timestamp=datetime.now(),
            latency_ms=latency_ms,
        )

        logger.info(
            f"Criteria evaluation complete: {decision.value} "
            f"(score={final_score:.2f}, {latency_ms}ms)"
        )

        return result

    async def _evaluate_criterion(
        self,
        provider: Any,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        criterion_name: str,
        criterion_description: str
    ) -> tuple[float, str]:
        """
        Evaluate a single criterion using the LLM.

        Returns:
            Tuple of (score 0-1, reasoning string)
        """
        prompt = f"""Evaluate this case against a SINGLE criterion.

Criterion: {criterion_name}
Description: {criterion_description}

Case Data:
{self._format_input_data(input_data)}

Instructions:
1. Assess how well the case meets this specific criterion
2. Provide a score from 0.0 to 1.0 where:
   - 0.0 = Does not meet criterion at all
   - 0.5 = Partially meets criterion
   - 1.0 = Fully meets criterion
3. Explain your scoring

Respond in this exact format:
SCORE: [0.0-1.0]
REASONING: [Your explanation]
"""

        system_context = context.get("system_context", context.get("policy_context", ""))

        try:
            response = await provider.generate_decision(
                prompt=prompt,
                system_context=system_context
            )

            # Parse score and reasoning from response
            content = response.content if hasattr(response, 'content') else str(response)
            score, reasoning = self._parse_criterion_response(content)

            return score, reasoning

        except Exception as e:
            logger.error(f"Error evaluating criterion '{criterion_name}': {e}")
            return 0.5, f"Error evaluating criterion: {str(e)}"

    def _parse_criterion_response(self, content: str) -> tuple[float, str]:
        """Parse LLM response to extract score and reasoning."""
        lines = content.strip().split('\n')
        score = 0.5
        reasoning = content

        for line in lines:
            line_lower = line.lower().strip()
            if line_lower.startswith('score:'):
                try:
                    score_str = line.split(':', 1)[1].strip()
                    # Handle various formats: "0.8", "0.8/1.0", "80%"
                    score_str = score_str.replace('%', '').split('/')[0].strip()
                    parsed_score = float(score_str)
                    if parsed_score > 1:
                        parsed_score = parsed_score / 100
                    score = max(0.0, min(1.0, parsed_score))
                except (ValueError, IndexError):
                    pass
            elif line_lower.startswith('reasoning:'):
                reasoning = line.split(':', 1)[1].strip()

        return score, reasoning

    def _aggregate_scores(
        self,
        criteria_scores: Dict[str, Dict[str, Any]]
    ) -> tuple[float, DecisionOutcome]:
        """
        Aggregate individual criterion scores into final score and decision.

        Returns:
            Tuple of (final_score, decision)
        """
        if not criteria_scores:
            return 0.0, DecisionOutcome.NEEDS_REVIEW

        # Check critical criteria first
        if self.require_all_critical:
            for name, data in criteria_scores.items():
                if data.get("critical") and not data.get("passed"):
                    logger.info(f"Critical criterion '{name}' failed - requires review")
                    return data["score"], DecisionOutcome.NEEDS_REVIEW

        # Aggregate based on method
        if self.aggregation == "min":
            final_score = min(d["score"] for d in criteria_scores.values())

        elif self.aggregation == "all_pass":
            all_passed = all(d["passed"] for d in criteria_scores.values())
            final_score = 1.0 if all_passed else 0.0

        else:  # weighted_avg (default)
            total_weight = sum(d["weight"] for d in criteria_scores.values())
            if total_weight == 0:
                final_score = 0.0
            else:
                weighted_sum = sum(
                    d["score"] * d["weight"] for d in criteria_scores.values()
                )
                final_score = weighted_sum / total_weight

        # Determine decision
        if final_score >= self.passing_threshold:
            decision = DecisionOutcome.APPROVED
        elif final_score <= (1 - self.passing_threshold):
            decision = DecisionOutcome.DENIED
        else:
            decision = DecisionOutcome.NEEDS_REVIEW

        return final_score, decision

    def _build_reasoning(
        self,
        criteria_scores: Dict[str, Dict[str, Any]],
        final_score: float,
        decision: DecisionOutcome
    ) -> str:
        """Build human-readable reasoning from criteria scores."""
        passed = [n for n, d in criteria_scores.items() if d["passed"]]
        failed = [n for n, d in criteria_scores.items() if not d["passed"]]

        reasoning = f"Criteria decomposition result: {decision.value} (score: {final_score:.2f})\n\n"

        if passed:
            reasoning += f"Passed ({len(passed)}): {', '.join(passed)}\n"
        if failed:
            reasoning += f"Failed ({len(failed)}): {', '.join(failed)}\n"

        reasoning += f"\nAggregation method: {self.aggregation}, threshold: {self.passing_threshold}"

        return reasoning

    def _format_input_data(self, input_data: Dict[str, Any]) -> str:
        """Format input data for prompt."""
        return "\n".join([f"- {k}: {v}" for k, v in input_data.items()])

    def _generate_default_criteria(self, decision_type: str) -> List[Dict[str, Any]]:
        """Generate default criteria based on decision type."""
        default_criteria = {
            "unemployment_benefits": [
                {"name": "employment_duration", "description": "Met minimum employment duration requirement", "weight": 1.0, "critical": True},
                {"name": "termination_reason", "description": "Termination was through no fault of applicant", "weight": 1.2, "critical": True},
                {"name": "availability", "description": "Available and actively seeking work", "weight": 1.0},
                {"name": "earnings_history", "description": "Meets minimum earnings requirements", "weight": 0.8},
            ],
            "hiring": [
                {"name": "experience", "description": "Has required years of relevant experience", "weight": 1.0},
                {"name": "skills", "description": "Possesses required technical skills", "weight": 1.2, "critical": True},
                {"name": "education", "description": "Has required education or equivalent", "weight": 0.8},
                {"name": "culture_fit", "description": "Aligns with team and company values", "weight": 0.6},
            ],
            "loan_approval": [
                {"name": "credit_score", "description": "Credit score meets minimum threshold", "weight": 1.2, "critical": True},
                {"name": "income", "description": "Income sufficient for loan payments", "weight": 1.0, "critical": True},
                {"name": "debt_ratio", "description": "Debt-to-income ratio is acceptable", "weight": 1.0},
                {"name": "employment_stability", "description": "Has stable employment history", "weight": 0.8},
            ],
        }

        return default_criteria.get(decision_type, [
            {"name": "eligibility", "description": "Meets basic eligibility requirements", "weight": 1.0},
            {"name": "completeness", "description": "Application is complete with required information", "weight": 0.8},
            {"name": "compliance", "description": "Meets regulatory compliance requirements", "weight": 1.0},
        ])
