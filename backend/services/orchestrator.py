"""
Decision Orchestrator for TrustChain.

Coordinates multiple AI models to make consensus-based decisions with
full audit trails and bias detection.

Built with 🤝 by Kareem & Claude (January 2025)
"Making AI accountable, one decision at a time"
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from providers import (
    BaseLLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    LlamaProvider,
    ProviderConfig,
    LLMResponse,
    ModelProvider
)

from models import (
    Decision,
    ModelDecision,
    DecisionOutcome,
    DecisionStatus,
    ConsensusAnalysis
)

from .bias_detection import get_bias_detector

logger = logging.getLogger(__name__)


class DecisionOrchestrator:
    """
    Orchestrates multiple AI models to make consensus-based decisions.

    This is the "train conductor" - it coordinates all the AI models,
    runs them in parallel, and analyzes their agreement/disagreement.
    """

    def __init__(
        self,
        anthropic_config: Optional[ProviderConfig] = None,
        openai_config: Optional[ProviderConfig] = None,
        llama_config: Optional[ProviderConfig] = None,
        require_consensus_threshold: float = 0.66  # 2 out of 3 models must agree
    ):
        """
        Initialize the orchestrator with AI provider configurations.

        Args:
            anthropic_config: Configuration for Claude (optional)
            openai_config: Configuration for GPT (optional)
            llama_config: Configuration for Llama (optional)
            require_consensus_threshold: Minimum agreement required (0.66 = 66% = 2/3 models)

        Note: At least 2 providers should be configured for meaningful consensus.
        """
        self.providers: List[BaseLLMProvider] = []
        self.consensus_threshold = require_consensus_threshold

        # Initialize providers that have configurations
        if anthropic_config:
            self.providers.append(AnthropicProvider(config=anthropic_config))
            logger.info("✓ Anthropic provider initialized")

        if openai_config:
            self.providers.append(OpenAIProvider(config=openai_config))
            logger.info("✓ OpenAI provider initialized")

        if llama_config:
            self.providers.append(LlamaProvider(config=llama_config))
            logger.info("✓ Llama provider initialized")

        if len(self.providers) < 2:
            logger.warning(
                "⚠️  Only one provider configured. Consensus requires at least 2 models."
            )

        logger.info(
            f"Orchestrator initialized with {len(self.providers)} providers, "
            f"consensus threshold: {self.consensus_threshold:.0%}"
        )

    async def make_decision(
        self,
        case_id: str,
        decision_type: str,
        prompt: str,
        policy_context: str,
        input_data: Dict[str, Any]
    ) -> Decision:
        """
        Make a consensus decision using multiple AI models.

        This is the MAIN method - it's like the train conductor's control panel.
        Here's what it does step-by-step:

        1. Send the same question to all AI models IN PARALLEL
        2. Wait for all responses (or timeout)
        3. Convert responses to standardized format
        4. Analyze consensus (do they agree?)
        5. Create final decision with audit trail
        6. Return complete Decision object

        Args:
            case_id: Unique identifier for this case (e.g., "unemp_app_987654")
            decision_type: Type of decision (e.g., "unemployment_benefits")
            prompt: The actual question/case details to send to AI models
            policy_context: Government policy and legal requirements
            input_data: Raw application data for audit trail

        Returns:
            Decision object with all model responses and consensus analysis

        Example:
            decision = await orchestrator.make_decision(
                case_id="unemp_app_001",
                decision_type="unemployment_benefits",
                prompt="Applicant worked 18 months, laid off...",
                policy_context="State unemployment eligibility rules...",
                input_data={"employment_months": 18, ...}
            )
        """
        logger.info(f"🚀 Starting decision for case: {case_id}")

        # Create the Decision object that will hold everything
        decision = Decision(
            decision_id=f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{case_id}",
            case_id=case_id,
            decision_type=decision_type,
            input_data=input_data,
            policy_context=policy_context,
            status=DecisionStatus.IN_PROGRESS
        )

        # STEP 1: Query all models IN PARALLEL
        logger.info(f"📡 Querying {len(self.providers)} AI models in parallel...")
        llm_responses = await self._query_all_providers(prompt, policy_context)

        # STEP 2: Convert LLM responses to ModelDecision objects
        logger.info(f"📊 Processing {len(llm_responses)} model responses...")
        decision.model_decisions = self._convert_to_model_decisions(llm_responses)

        # STEP 3: Analyze consensus
        logger.info("🔍 Analyzing consensus across models...")
        decision.consensus_analysis = self._analyze_consensus(decision.model_decisions)

        # STEP 3.5: CRITICAL SAFETY CHECK - Bias Detection
        logger.info("🛡️  Running bias detection and safety analysis...")
        bias_detector = get_bias_detector(strict_mode=True, confidence_threshold=0.7)
        decision.bias_analysis = bias_detector.analyze_decision(
            model_decisions=decision.model_decisions,
            consensus_analysis=decision.consensus_analysis,
            decision_type=decision_type,
            input_data=input_data
        )

        # Check if mandatory human review is required (overrides consensus)
        requires_mandatory_review = bias_detector.requires_mandatory_review(
            bias_analysis=decision.bias_analysis,
            decision_type=decision_type,
            consensus_level=decision.consensus_analysis.agreement_level
        )

        # STEP 4: Determine final decision
        decision.final_decision = decision.consensus_analysis.majority_decision

        # STEP 5: Check if human review is needed
        if requires_mandatory_review:
            decision.status = DecisionStatus.REQUIRES_REVIEW
            logger.critical(
                f"🚨 MANDATORY HUMAN REVIEW REQUIRED\n"
                f"   Reason: {decision.bias_analysis.recommendation}"
            )
        elif decision.consensus_analysis.agreement_level < self.consensus_threshold:
            decision.status = DecisionStatus.REQUIRES_REVIEW
            logger.warning(
                f"⚠️  Low consensus ({decision.consensus_analysis.agreement_level:.0%}) "
                f"- flagging for human review"
            )
        else:
            decision.status = DecisionStatus.COMPLETED
            logger.info(
                f"✅ High consensus ({decision.consensus_analysis.agreement_level:.0%}) "
                f"- decision: {decision.final_decision.value}"
            )

        # STEP 6: Generate audit hash for tamper detection
        decision.completed_at = datetime.now()
        decision.audit_hash = decision.calculate_audit_hash()

        logger.info(f"✅ Decision complete: {decision.decision_id}")
        return decision

    async def _query_all_providers(
        self,
        prompt: str,
        policy_context: str
    ) -> List[LLMResponse]:
        """
        Query all AI providers IN PARALLEL and collect their responses.

        This is where the magic happens! Instead of asking each AI one by one,
        we ask them ALL AT THE SAME TIME using asyncio.gather().

        Args:
            prompt: The question to ask all models
            policy_context: Government policy context

        Returns:
            List of LLMResponse objects (one from each provider)

        How asyncio.gather() works:
            # Sequential (slow):
            r1 = await provider1.generate_decision(...)  # Wait 2s
            r2 = await provider2.generate_decision(...)  # Wait 2s
            r3 = await provider3.generate_decision(...)  # Wait 2s
            Total: 6 seconds

            # Parallel (fast):
            responses = await asyncio.gather(
                provider1.generate_decision(...),
                provider2.generate_decision(...),
                provider3.generate_decision(...)
            )
            Total: 2 seconds (all run simultaneously!)
        """
        # Create a list of tasks (one for each provider)
        tasks = [
            provider.generate_decision(
                prompt=prompt,
                system_context=policy_context
            )
            for provider in self.providers
        ]

        # Execute all tasks in parallel and wait for ALL to complete
        # return_exceptions=True means if one fails, others continue
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions (failed providers)
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(
                    f"❌ Provider {self.providers[i].provider.value} failed: {str(response)}"
                )
            elif response.error:
                logger.warning(
                    f"⚠️  Provider {response.provider.value} returned error: {response.error}"
                )
            else:
                valid_responses.append(response)
                logger.info(
                    f"✅ {response.provider.value}: {response.content[:50]}..."
                )

        if not valid_responses:
            logger.error("❌ All providers failed!")
            raise Exception("All AI providers failed to respond")

        logger.info(f"✅ Received {len(valid_responses)}/{len(self.providers)} valid responses")
        return valid_responses

    def _convert_to_model_decisions(
        self,
        llm_responses: List[LLMResponse]
    ) -> List[ModelDecision]:
        """
        Convert LLMResponse objects to ModelDecision objects.

        Why do we need this conversion?
        - LLMResponse is the RAW output from providers (technical details)
        - ModelDecision is the BUSINESS logic format (what was decided)

        This also parses the AI's response to extract the actual decision
        (APPROVE, DENY, etc.) from the text content.

        Args:
            llm_responses: Raw responses from AI providers

        Returns:
            List of ModelDecision objects ready for consensus analysis
        """
        model_decisions = []

        for response in llm_responses:
            # Extract the decision from the AI's text response
            decision_outcome = self._parse_decision_outcome(response.content)

            # Create ModelDecision object
            model_decision = ModelDecision(
                model_provider=response.provider.value,
                model_name=response.model_name,
                decision=decision_outcome,
                reasoning=response.reasoning or response.content[:500],  # First 500 chars if no reasoning
                confidence=response.confidence or 0.5,
                timestamp=response.timestamp,
                tokens_used=response.tokens_used,
                latency_ms=response.latency_ms,
                metadata=response.metadata
            )

            model_decisions.append(model_decision)
            logger.debug(
                f"Converted {response.provider.value} response to decision: {decision_outcome.value}"
            )

        return model_decisions

    def _parse_decision_outcome(self, content: str) -> DecisionOutcome:
        """
        Parse the AI's text response to extract the decision.

        AI models return text like:
        "Based on the criteria, I recommend APPROVAL because..."
        "This application should be DENIED due to..."

        We need to extract: APPROVED or DENIED

        Args:
            content: The AI's text response

        Returns:
            DecisionOutcome enum (APPROVED, DENIED, NEEDS_HUMAN_REVIEW, etc.)
        """
        content_lower = content.lower()

        # Look for approval keywords
        approval_keywords = [
            "approve", "approved", "approval", "grant", "granted",
            "accept", "accepted", "eligible", "qualify", "qualifies"
        ]

        # Look for denial keywords
        denial_keywords = [
            "deny", "denied", "denial", "reject", "rejected",
            "ineligible", "disqualify", "disqualified"
        ]

        # Look for uncertainty keywords
        review_keywords = [
            "unclear", "uncertain", "needs review", "human review",
            "unable to determine", "insufficient information"
        ]

        # Count keyword matches
        approval_count = sum(1 for keyword in approval_keywords if keyword in content_lower)
        denial_count = sum(1 for keyword in denial_keywords if keyword in content_lower)
        review_count = sum(1 for keyword in review_keywords if keyword in content_lower)

        # Determine decision based on keyword counts
        if review_count > 0:
            return DecisionOutcome.NEEDS_HUMAN_REVIEW

        if approval_count > denial_count:
            return DecisionOutcome.APPROVED
        elif denial_count > approval_count:
            return DecisionOutcome.DENIED
        else:
            # Ambiguous - flag for review
            logger.warning(f"Ambiguous decision in response: {content[:100]}...")
            return DecisionOutcome.NEEDS_HUMAN_REVIEW

    def _analyze_consensus(
        self,
        model_decisions: List[ModelDecision]
    ) -> ConsensusAnalysis:
        """
        Analyze consensus among model decisions.

        This is the HEART of TrustChain! This method answers:
        - Do the AI models agree?
        - Which decision has majority support?
        - How much do they disagree?
        - Should we trust this, or flag for human review?

        Algorithm:
        1. Count votes for each decision (APPROVE, DENY, etc.)
        2. Find the majority decision (most votes)
        3. Calculate agreement level (what % agree with majority)
        4. Calculate confidence variance (how uncertain are they)
        5. Identify dissenting models

        Args:
            model_decisions: List of decisions from each AI model

        Returns:
            ConsensusAnalysis with agreement metrics

        Example:
            Models: [APPROVE, APPROVE, DENY]
            Majority: APPROVE (2/3 = 66%)
            Agreement: 0.66
            Dissenting: [llama]
        """
        if not model_decisions:
            raise ValueError("Cannot analyze consensus with no model decisions")

        # STEP 1: Count votes for each decision type
        decision_counts = {}
        for model_decision in model_decisions:
            decision = model_decision.decision
            decision_counts[decision] = decision_counts.get(decision, 0) + 1

        logger.debug(f"Decision vote counts: {decision_counts}")

        # STEP 2: Find the majority decision (most votes)
        majority_decision = max(decision_counts, key=decision_counts.get)
        majority_count = decision_counts[majority_decision]

        logger.info(
            f"Majority decision: {majority_decision.value} "
            f"({majority_count}/{len(model_decisions)} models)"
        )

        # STEP 3: Calculate agreement level
        # agreement_level = (# models agreeing with majority) / (total # models)
        agreement_level = majority_count / len(model_decisions)

        # STEP 4: Find dissenting models (those who disagreed with majority)
        dissenting_models = []
        for model_decision in model_decisions:
            if model_decision.decision != majority_decision:
                dissenting_models.append(model_decision.model_provider)

        # STEP 5: Calculate confidence variance
        # How much do confidence scores vary? Low variance = models are similarly confident
        confidences = [md.confidence for md in model_decisions]
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)

        logger.debug(f"Confidence variance: {variance:.4f}, Mean: {mean_confidence:.2f}")

        # STEP 6: Analyze reasoning divergence
        reasoning_divergence = None
        if dissenting_models:
            reasoning_divergence = (
                f"{len(dissenting_models)} model(s) disagreed: {', '.join(dissenting_models)}. "
                f"Majority chose {majority_decision.value} with {agreement_level:.0%} agreement."
            )

        # Create the ConsensusAnalysis object
        consensus = ConsensusAnalysis(
            agreement_level=agreement_level,
            majority_decision=majority_decision,
            dissenting_models=dissenting_models,
            confidence_variance=variance,
            reasoning_divergence=reasoning_divergence
        )

        logger.info(
            f"Consensus analysis complete: {agreement_level:.0%} agreement, "
            f"variance: {variance:.4f}"
        )

        return consensus

    def get_provider_health(self) -> Dict[str, Any]:
        """
        Get health status of all providers.

        Useful for monitoring dashboards and debugging.

        Returns:
            Dictionary with health metrics for each provider
        """
        health_status = {
            "total_providers": len(self.providers),
            "providers": []
        }

        for provider in self.providers:
            metrics = provider.get_metrics()
            health_status["providers"].append(metrics)

        # Calculate overall health
        healthy_count = sum(
            1 for p in self.providers
            if p.get_status().value == "healthy"
        )
        health_status["healthy_providers"] = healthy_count
        health_status["overall_health"] = healthy_count / len(self.providers) if self.providers else 0

        return health_status
