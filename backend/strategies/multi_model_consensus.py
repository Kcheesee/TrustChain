"""
Multi-Model Consensus Strategy for TrustChain.

This strategy establishes accountability by querying multiple AI models
in parallel and using weighted consensus voting to determine decisions.

Refactored from the original orchestrator.py to fit the plugin architecture.

Built with care by Kareem & Claude
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import Counter

from core.base import BaseStrategy
from core.registry import register_component
from core.result import StrategyResult, DecisionOutcome

logger = logging.getLogger(__name__)


@register_component
class MultiModelConsensusStrategy(BaseStrategy):
    """
    Multi-model consensus evaluation strategy.

    Queries multiple AI models in parallel and uses weighted voting
    to determine the final decision. This is the original TrustChain
    accountability method.

    How it works:
    1. Send the same prompt to all configured LLM providers in parallel
    2. Parse each response to extract decision (APPROVE/DENY/etc.)
    3. Calculate weighted consensus across all models
    4. Return combined result with agreement metrics

    Configuration options:
        consensus_threshold: Minimum agreement required (default 0.66 = 2/3)
        use_confidence_weighting: Multiply votes by confidence (default True)
        provider_weights: Custom weights per provider (default all 1.0)
        min_confidence_threshold: Minimum confidence to include vote (default 0.5)

    Example:
        strategy = MultiModelConsensusStrategy(config={
            "consensus_threshold": 0.66,
            "provider_weights": {"anthropic": 1.0, "openai": 1.0, "llama": 0.8}
        })
        result = await strategy.evaluate(input_data, context, providers)
    """

    name = "multi_model_consensus"
    description = "Query multiple AI models and use weighted consensus voting"
    version = "1.0.0"
    requires_multiple_providers = True
    min_providers = 2

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the multi-model consensus strategy."""
        super().__init__(config)

        # Configuration with defaults
        self.consensus_threshold = self.config.get("consensus_threshold", 0.66)
        self.use_confidence_weighting = self.config.get("use_confidence_weighting", True)
        self.provider_weights = self.config.get("provider_weights", {
            "anthropic": 1.0,
            "openai": 1.0,
            "llama": 0.8
        })
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.5)

        logger.info(
            f"MultiModelConsensusStrategy initialized: "
            f"threshold={self.consensus_threshold:.0%}, "
            f"confidence_weighting={self.use_confidence_weighting}"
        )

    def set_model_weights(self, weights: Dict[str, float]) -> None:
        """
        Set model weights from learned parameters.

        This is the Phase 3 learning hook - adjusts voting weights
        based on individual model accuracy from human feedback.

        Args:
            weights: Dict mapping model_id/provider to weight
        """
        for model_id, weight in weights.items():
            # Try exact match first
            if model_id in self.provider_weights:
                old_weight = self.provider_weights[model_id]
                self.provider_weights[model_id] = weight
                logger.info(f"Adjusted weight for {model_id}: {old_weight:.2f} -> {weight:.2f}")
            else:
                # Try matching by provider prefix (e.g., "anthropic/claude-3" -> "anthropic")
                provider = model_id.split("/")[0] if "/" in model_id else model_id
                if provider in self.provider_weights:
                    old_weight = self.provider_weights[provider]
                    self.provider_weights[provider] = weight
                    logger.info(f"Adjusted weight for {provider}: {old_weight:.2f} -> {weight:.2f}")

    def get_model_weights(self) -> Dict[str, float]:
        """Get current model weights (for inspection/debugging)."""
        return self.provider_weights.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration."""
        if "consensus_threshold" in config:
            threshold = config["consensus_threshold"]
            if not 0 < threshold <= 1:
                raise ValueError("consensus_threshold must be between 0 and 1")

        if "min_confidence_threshold" in config:
            min_conf = config["min_confidence_threshold"]
            if not 0 <= min_conf <= 1:
                raise ValueError("min_confidence_threshold must be between 0 and 1")

        return True

    async def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        providers: List[Any]
    ) -> StrategyResult:
        """
        Execute multi-model consensus evaluation.

        Args:
            input_data: The case/application data to evaluate
            context: Policy context with 'prompt' and 'system_context' keys
            providers: List of LLM provider instances

        Returns:
            StrategyResult with consensus decision and agreement metrics
        """
        start_time = datetime.now()

        if len(providers) < self.min_providers:
            logger.warning(
                f"Only {len(providers)} providers available, "
                f"recommended minimum is {self.min_providers}"
            )

        # Extract prompt from context
        prompt = context.get("prompt", "")
        system_context = context.get("system_context", context.get("policy_context", ""))

        if not prompt:
            # Build prompt from input_data if not provided
            prompt = self._build_prompt(input_data, context)

        logger.info(f"Querying {len(providers)} AI models in parallel...")

        # STEP 1: Query all providers in parallel
        llm_responses = await self._query_all_providers(
            providers, prompt, system_context
        )

        if not llm_responses:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="All AI providers failed to respond",
                timestamp=datetime.now(),
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

        # STEP 2: Convert responses to model decisions
        model_decisions = self._convert_responses(llm_responses)

        # STEP 3: Calculate weighted consensus
        consensus = self._calculate_consensus(model_decisions)

        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        total_tokens = sum(r.get("tokens_used", 0) for r in llm_responses if r.get("tokens_used"))

        # Build result
        result = StrategyResult(
            strategy_name=self.name,
            decision=consensus["majority_decision"],
            confidence=consensus["avg_confidence"],
            reasoning=self._build_reasoning(consensus, model_decisions),
            model_decisions=model_decisions,
            agreement_level=consensus["agreement_level"],
            dissenting_views=consensus["dissenting_reasonings"],
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            tokens_used=total_tokens if total_tokens > 0 else None,
            raw_responses=llm_responses
        )

        logger.info(
            f"Consensus result: {result.decision.value} "
            f"({result.agreement_level:.0%} agreement, {latency_ms}ms)"
        )

        return result

    async def _query_all_providers(
        self,
        providers: List[Any],
        prompt: str,
        system_context: str
    ) -> List[Dict[str, Any]]:
        """
        Query all AI providers in parallel.

        Uses asyncio.gather to execute all requests simultaneously,
        reducing total latency to the time of the slowest provider.
        """
        tasks = [
            provider.generate_decision(
                prompt=prompt,
                system_context=system_context
            )
            for provider in providers
        ]

        # Execute all tasks in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses, filtering out failures
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Provider {i} failed: {str(response)}")
                continue

            if hasattr(response, 'error') and response.error:
                logger.warning(f"Provider returned error: {response.error}")
                continue

            # Convert LLMResponse to dict for storage
            response_dict = {
                "provider": getattr(response, 'provider', providers[i].__class__.__name__).value if hasattr(getattr(response, 'provider', None), 'value') else str(getattr(response, 'provider', 'unknown')),
                "model_name": getattr(response, 'model_name', 'unknown'),
                "content": getattr(response, 'content', ''),
                "reasoning": getattr(response, 'reasoning', ''),
                "confidence": getattr(response, 'confidence', 0.5),
                "tokens_used": getattr(response, 'tokens_used', None),
                "latency_ms": getattr(response, 'latency_ms', None),
            }
            valid_responses.append(response_dict)
            logger.debug(f"Valid response from {response_dict['provider']}")

        logger.info(f"Received {len(valid_responses)}/{len(providers)} valid responses")
        return valid_responses

    def _convert_responses(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert raw responses to structured model decision dicts."""
        model_decisions = []

        for response in responses:
            decision_outcome = self._parse_decision_outcome(response.get("content", ""))

            model_decisions.append({
                "provider": response.get("provider", "unknown"),
                "model_name": response.get("model_name", "unknown"),
                "decision": decision_outcome.value,
                "reasoning": response.get("reasoning") or response.get("content", "")[:500],
                "confidence": response.get("confidence", 0.5),
            })

        return model_decisions

    def _parse_decision_outcome(self, content: str) -> DecisionOutcome:
        """Parse AI response text to extract decision outcome."""
        content_lower = content.lower()

        approval_keywords = [
            "approve", "approved", "approval", "grant", "granted",
            "accept", "accepted", "eligible", "qualify", "qualifies"
        ]

        denial_keywords = [
            "deny", "denied", "denial", "reject", "rejected",
            "ineligible", "disqualify", "disqualified"
        ]

        review_keywords = [
            "unclear", "uncertain", "needs review", "human review",
            "unable to determine", "insufficient information"
        ]

        approval_count = sum(1 for kw in approval_keywords if kw in content_lower)
        denial_count = sum(1 for kw in denial_keywords if kw in content_lower)
        review_count = sum(1 for kw in review_keywords if kw in content_lower)

        if review_count > 0:
            return DecisionOutcome.NEEDS_REVIEW

        if approval_count > denial_count:
            return DecisionOutcome.APPROVED
        elif denial_count > approval_count:
            return DecisionOutcome.DENIED
        else:
            return DecisionOutcome.NEEDS_REVIEW

    def _calculate_consensus(self, model_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate weighted consensus from model decisions."""
        if not model_decisions:
            return {
                "majority_decision": DecisionOutcome.NEEDS_REVIEW,
                "agreement_level": 0.0,
                "avg_confidence": 0.0,
                "dissenting_models": [],
                "dissenting_reasonings": [],
            }

        # Filter by confidence threshold
        valid_decisions = [
            d for d in model_decisions
            if d.get("confidence", 0) >= self.min_confidence_threshold
        ] or model_decisions

        # Calculate weighted votes
        weighted_votes: Dict[str, float] = {}
        total_weight = 0.0

        for decision in valid_decisions:
            provider = decision.get("provider", "unknown")
            outcome = decision.get("decision", "needs_review")
            confidence = decision.get("confidence", 0.5)

            base_weight = self.provider_weights.get(provider, 1.0)
            weight = base_weight * confidence if self.use_confidence_weighting else base_weight

            weighted_votes[outcome] = weighted_votes.get(outcome, 0.0) + weight
            total_weight += weight

        # Find majority
        majority_decision_str = max(weighted_votes, key=weighted_votes.get)
        majority_weight = weighted_votes[majority_decision_str]

        # Convert string back to enum
        try:
            majority_decision = DecisionOutcome(majority_decision_str)
        except ValueError:
            majority_decision = DecisionOutcome.NEEDS_REVIEW

        # Calculate agreement level
        agreement_level = majority_weight / total_weight if total_weight > 0 else 0.0

        # Find dissenting models
        dissenting_models = []
        dissenting_reasonings = []
        for d in valid_decisions:
            if d.get("decision") != majority_decision_str:
                dissenting_models.append(d.get("provider", "unknown"))
                dissenting_reasonings.append(d.get("reasoning", "")[:200])

        # Calculate average confidence
        confidences = [d.get("confidence", 0.5) for d in valid_decisions]
        avg_confidence = sum(confidences) / len(confidences)

        return {
            "majority_decision": majority_decision,
            "agreement_level": agreement_level,
            "avg_confidence": avg_confidence,
            "dissenting_models": dissenting_models,
            "dissenting_reasonings": dissenting_reasonings,
            "vote_distribution": weighted_votes,
        }

    def _build_reasoning(
        self,
        consensus: Dict[str, Any],
        model_decisions: List[Dict[str, Any]]
    ) -> str:
        """Build human-readable reasoning summary."""
        decision = consensus["majority_decision"]
        agreement = consensus["agreement_level"]
        dissenting = consensus.get("dissenting_models", [])

        reasoning = (
            f"Multi-model consensus reached {decision.value} decision "
            f"with {agreement:.0%} agreement across {len(model_decisions)} models."
        )

        if dissenting:
            reasoning += f" Dissenting: {', '.join(dissenting)}."

        return reasoning

    def _build_prompt(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build evaluation prompt from input data and context."""
        decision_type = context.get("decision_type", "general evaluation")

        prompt = f"Please evaluate this {decision_type} case:\n\n"

        for key, value in input_data.items():
            prompt += f"- {key}: {value}\n"

        prompt += "\nProvide your decision (APPROVE, DENY, or NEEDS_REVIEW) with reasoning."

        return prompt
