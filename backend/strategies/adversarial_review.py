"""
Adversarial Review Strategy for TrustChain.

This strategy generates a decision, then actively challenges it with
counter-arguments. If the challenge succeeds (finds valid reasons to
overturn), the decision requires human review.

The process:
1. Initial evaluation → APPROVE/DENY decision
2. Devil's advocate pass → Try to find flaws in the decision
3. Defense pass → Address the challenges
4. Final verdict → Does the decision survive scrutiny?

This catches:
- Overconfident decisions
- Edge cases missed by single-pass evaluation
- Weak reasoning that doesn't hold up to challenge

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
class AdversarialReviewStrategy(BaseStrategy):
    """
    Adversarial review evaluation strategy.

    Makes an initial decision, then challenges it with counter-arguments.
    Decisions that can't withstand scrutiny are flagged for human review.

    Configuration options:
        challenge_strength: 'light', 'medium', 'aggressive' (default: medium)
        require_defense: If True, decision must successfully defend against challenges
        max_challenges: Maximum number of challenges to generate (default: 3)
        survival_threshold: Confidence needed after challenge to survive (default: 0.6)

    Example:
        strategy = AdversarialReviewStrategy(config={
            "challenge_strength": "medium",
            "require_defense": True,
            "max_challenges": 3
        })
    """

    name = "adversarial_review"
    description = "Challenge decisions with counter-arguments to catch weak reasoning"
    version = "1.0.0"
    requires_multiple_providers = False
    min_providers = 1

    CHALLENGE_PROMPTS = {
        "light": "Identify any minor concerns or edge cases that might affect this decision.",
        "medium": "Act as a skeptical reviewer. Find weaknesses, inconsistencies, or overlooked factors that could change this decision.",
        "aggressive": "Act as an aggressive defense attorney. Find every possible reason why this decision is WRONG. Challenge assumptions, find loopholes, identify risks."
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize adversarial review strategy."""
        super().__init__(config)

        self.challenge_strength = self.config.get("challenge_strength", "medium")
        self.require_defense = self.config.get("require_defense", True)
        self.max_challenges = self.config.get("max_challenges", 3)
        self.survival_threshold = self.config.get("survival_threshold", 0.6)

        logger.info(
            f"AdversarialReviewStrategy initialized: "
            f"strength={self.challenge_strength}, "
            f"max_challenges={self.max_challenges}"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration."""
        valid_strengths = ["light", "medium", "aggressive"]
        if "challenge_strength" in config and config["challenge_strength"] not in valid_strengths:
            raise ValueError(f"challenge_strength must be one of: {valid_strengths}")

        if "survival_threshold" in config:
            threshold = config["survival_threshold"]
            if not 0 <= threshold <= 1:
                raise ValueError("survival_threshold must be between 0 and 1")

        return True

    async def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        providers: List[Any]
    ) -> StrategyResult:
        """
        Execute adversarial review evaluation.

        Args:
            input_data: Case data to evaluate
            context: Policy context
            providers: Available LLM providers

        Returns:
            StrategyResult with challenge details and survival status
        """
        start_time = datetime.now()

        if not providers:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="No LLM providers available",
            )

        provider = providers[0]
        system_context = context.get("system_context", context.get("policy_context", ""))

        # STEP 1: Initial evaluation
        logger.info("Step 1: Initial evaluation...")
        initial_decision, initial_reasoning, initial_confidence = await self._initial_evaluation(
            provider, input_data, context, system_context
        )

        logger.info(f"  Initial: {initial_decision.value} ({initial_confidence:.0%})")

        # STEP 2: Generate challenges
        logger.info("Step 2: Generating adversarial challenges...")
        challenges = await self._generate_challenges(
            provider, input_data, initial_decision, initial_reasoning, system_context
        )

        logger.info(f"  Generated {len(challenges)} challenges")

        # STEP 3: Defend against challenges (if required)
        defense_results = []
        if self.require_defense and challenges:
            logger.info("Step 3: Defending against challenges...")
            defense_results = await self._defend_challenges(
                provider, input_data, initial_decision, initial_reasoning, challenges, system_context
            )

        # STEP 4: Determine if decision survives
        survived, final_confidence, final_reasoning = self._evaluate_survival(
            initial_decision, initial_confidence, initial_reasoning,
            challenges, defense_results
        )

        # Determine final decision
        if not survived:
            final_decision = DecisionOutcome.NEEDS_REVIEW
            final_reasoning = (
                f"Decision did not survive adversarial review. "
                f"Original: {initial_decision.value}. "
                f"{len(challenges)} challenges raised, decision requires human review."
            )
        else:
            final_decision = initial_decision

        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        result = StrategyResult(
            strategy_name=self.name,
            decision=final_decision,
            confidence=final_confidence,
            reasoning=final_reasoning,
            challenges=[
                {
                    "challenge": c["challenge"],
                    "severity": c["severity"],
                    "defense": next(
                        (d["defense"] for d in defense_results if d["challenge_id"] == i),
                        None
                    ),
                    "defended": next(
                        (d["successfully_defended"] for d in defense_results if d["challenge_id"] == i),
                        False
                    ),
                }
                for i, c in enumerate(challenges)
            ],
            challenge_survived=survived,
            model_decisions=[{
                "provider": provider.__class__.__name__,
                "initial_decision": initial_decision.value,
                "initial_confidence": initial_confidence,
                "final_decision": final_decision.value,
                "final_confidence": final_confidence,
                "challenges_faced": len(challenges),
                "survived": survived,
            }],
            timestamp=datetime.now(),
            latency_ms=latency_ms,
        )

        logger.info(
            f"Adversarial review complete: {final_decision.value} "
            f"(survived={survived}, {latency_ms}ms)"
        )

        return result

    async def _initial_evaluation(
        self,
        provider: Any,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        system_context: str
    ) -> tuple[DecisionOutcome, str, float]:
        """Perform initial evaluation."""
        prompt = context.get("prompt", self._build_initial_prompt(input_data, context))

        try:
            response = await provider.generate_decision(
                prompt=prompt,
                system_context=system_context
            )

            content = response.content if hasattr(response, 'content') else str(response)
            decision = self._parse_decision(content)
            confidence = response.confidence if hasattr(response, 'confidence') else 0.7
            reasoning = response.reasoning if hasattr(response, 'reasoning') else content[:500]

            return decision, reasoning, confidence

        except Exception as e:
            logger.error(f"Initial evaluation failed: {e}")
            return DecisionOutcome.NEEDS_REVIEW, str(e), 0.0

    async def _generate_challenges(
        self,
        provider: Any,
        input_data: Dict[str, Any],
        decision: DecisionOutcome,
        reasoning: str,
        system_context: str
    ) -> List[Dict[str, Any]]:
        """Generate adversarial challenges to the decision."""
        challenge_instruction = self.CHALLENGE_PROMPTS.get(
            self.challenge_strength,
            self.CHALLENGE_PROMPTS["medium"]
        )

        prompt = f"""You are reviewing an AI decision. Your job is to find problems.

DECISION: {decision.value}

REASONING:
{reasoning}

CASE DATA:
{self._format_input_data(input_data)}

INSTRUCTIONS:
{challenge_instruction}

Generate up to {self.max_challenges} specific challenges. For each challenge:
1. State the concern clearly
2. Rate severity: LOW, MEDIUM, or HIGH
3. Explain why this could change the decision

Format each challenge as:
CHALLENGE: [Your challenge]
SEVERITY: [LOW/MEDIUM/HIGH]
IMPACT: [Why this matters]
---
"""

        try:
            response = await provider.generate_decision(
                prompt=prompt,
                system_context="You are a critical reviewer looking for flaws in decisions."
            )

            content = response.content if hasattr(response, 'content') else str(response)
            return self._parse_challenges(content)

        except Exception as e:
            logger.error(f"Challenge generation failed: {e}")
            return []

    async def _defend_challenges(
        self,
        provider: Any,
        input_data: Dict[str, Any],
        decision: DecisionOutcome,
        reasoning: str,
        challenges: List[Dict[str, Any]],
        system_context: str
    ) -> List[Dict[str, Any]]:
        """Attempt to defend against each challenge."""
        defense_results = []

        for i, challenge in enumerate(challenges):
            prompt = f"""You must defend a decision against a challenge.

ORIGINAL DECISION: {decision.value}
ORIGINAL REASONING: {reasoning}

CHALLENGE:
{challenge['challenge']}

CASE DATA:
{self._format_input_data(input_data)}

Can the original decision be defended against this challenge?
If YES, explain how the decision still holds.
If NO, explain why the challenge is valid and the decision should be reconsidered.

Format:
DEFENSE: [Your defense or admission]
DEFENDED: [YES/NO]
"""

            try:
                response = await provider.generate_decision(
                    prompt=prompt,
                    system_context=system_context
                )

                content = response.content if hasattr(response, 'content') else str(response)
                defense, defended = self._parse_defense(content)

                defense_results.append({
                    "challenge_id": i,
                    "challenge": challenge["challenge"],
                    "defense": defense,
                    "successfully_defended": defended,
                })

            except Exception as e:
                logger.error(f"Defense failed for challenge {i}: {e}")
                defense_results.append({
                    "challenge_id": i,
                    "challenge": challenge["challenge"],
                    "defense": f"Error: {str(e)}",
                    "successfully_defended": False,
                })

        return defense_results

    def _evaluate_survival(
        self,
        initial_decision: DecisionOutcome,
        initial_confidence: float,
        initial_reasoning: str,
        challenges: List[Dict[str, Any]],
        defense_results: List[Dict[str, Any]]
    ) -> tuple[bool, float, str]:
        """Determine if the decision survives adversarial review."""
        if not challenges:
            return True, initial_confidence, initial_reasoning

        # Count high-severity undefended challenges
        high_severity_undefended = 0
        total_undefended = 0

        for challenge in challenges:
            challenge_id = challenges.index(challenge)
            defense = next(
                (d for d in defense_results if d["challenge_id"] == challenge_id),
                None
            )

            if not defense or not defense.get("successfully_defended"):
                total_undefended += 1
                if challenge.get("severity", "").upper() == "HIGH":
                    high_severity_undefended += 1

        # Decision fails if:
        # - Any HIGH severity challenge is undefended
        # - More than half of challenges are undefended
        if high_severity_undefended > 0:
            confidence_penalty = 0.3 * high_severity_undefended
            final_confidence = max(0, initial_confidence - confidence_penalty)
            survived = False
            reasoning = (
                f"Failed {high_severity_undefended} HIGH severity challenge(s). "
                f"Original decision: {initial_decision.value}. "
                f"Confidence reduced from {initial_confidence:.0%} to {final_confidence:.0%}."
            )
        elif total_undefended > len(challenges) / 2:
            confidence_penalty = 0.1 * total_undefended
            final_confidence = max(0, initial_confidence - confidence_penalty)
            survived = final_confidence >= self.survival_threshold
            reasoning = (
                f"Failed to defend {total_undefended}/{len(challenges)} challenges. "
                f"Confidence: {final_confidence:.0%}. "
                f"{'Survived' if survived else 'Did not survive'} adversarial review."
            )
        else:
            defended_count = len(challenges) - total_undefended
            confidence_boost = 0.05 * defended_count
            final_confidence = min(1.0, initial_confidence + confidence_boost)
            survived = True
            reasoning = (
                f"Successfully defended {defended_count}/{len(challenges)} challenges. "
                f"Decision {initial_decision.value} confirmed with {final_confidence:.0%} confidence."
            )

        return survived, final_confidence, reasoning

    def _parse_decision(self, content: str) -> DecisionOutcome:
        """Parse decision from response content."""
        content_lower = content.lower()

        if any(word in content_lower for word in ["approve", "approved", "grant", "accept", "eligible"]):
            return DecisionOutcome.APPROVED
        elif any(word in content_lower for word in ["deny", "denied", "reject", "ineligible"]):
            return DecisionOutcome.DENIED
        else:
            return DecisionOutcome.NEEDS_REVIEW

    def _parse_challenges(self, content: str) -> List[Dict[str, Any]]:
        """Parse challenges from response content."""
        challenges = []
        sections = content.split('---')

        for section in sections:
            if 'CHALLENGE:' in section.upper():
                challenge = {"challenge": "", "severity": "MEDIUM", "impact": ""}

                for line in section.split('\n'):
                    line_upper = line.upper().strip()
                    if line_upper.startswith('CHALLENGE:'):
                        challenge["challenge"] = line.split(':', 1)[1].strip()
                    elif line_upper.startswith('SEVERITY:'):
                        severity = line.split(':', 1)[1].strip().upper()
                        if severity in ["LOW", "MEDIUM", "HIGH"]:
                            challenge["severity"] = severity
                    elif line_upper.startswith('IMPACT:'):
                        challenge["impact"] = line.split(':', 1)[1].strip()

                if challenge["challenge"]:
                    challenges.append(challenge)

        return challenges[:self.max_challenges]

    def _parse_defense(self, content: str) -> tuple[str, bool]:
        """Parse defense response."""
        defense = content
        defended = False

        for line in content.split('\n'):
            line_upper = line.upper().strip()
            if line_upper.startswith('DEFENSE:'):
                defense = line.split(':', 1)[1].strip()
            elif line_upper.startswith('DEFENDED:'):
                defended_str = line.split(':', 1)[1].strip().upper()
                defended = defended_str in ["YES", "TRUE", "1"]

        return defense, defended

    def _build_initial_prompt(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build initial evaluation prompt."""
        decision_type = context.get("decision_type", "general")
        formatted_data = self._format_input_data(input_data)

        return f"""Evaluate this {decision_type} case:

{formatted_data}

Provide your decision (APPROVE, DENY, or NEEDS_REVIEW) with reasoning.
"""

    def _format_input_data(self, input_data: Dict[str, Any]) -> str:
        """Format input data for prompts."""
        return "\n".join([f"- {k}: {v}" for k, v in input_data.items()])
