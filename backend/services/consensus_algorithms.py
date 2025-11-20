"""
Consensus Algorithms for TrustChain.

Implements various consensus mechanisms for combining multiple AI model decisions:
- Simple majority voting (baseline)
- Weighted voting (provider + confidence based)
- Bayesian consensus (future)

Built with 🤝 by Kareem & Claude (January 2025)
"Making AI accountable, one decision at a time"
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from collections import Counter

from models import ModelDecision, DecisionOutcome, ConsensusAnalysis

logger = logging.getLogger(__name__)


class ConsensusAlgorithm(str, Enum):
    """Available consensus algorithms."""
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_VOTING = "weighted_voting"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    BAYESIAN = "bayesian"  # Future implementation


class WeightedConsensusCalculator:
    """
    Calculate consensus using weighted voting.
    
    Allows different AI providers to have different weights based on:
    - Provider reliability/trust score
    - Model confidence level
    - Historical accuracy
    
    Example:
        calculator = WeightedConsensusCalculator(
            provider_weights={"anthropic": 1.0, "openai": 1.0, "llama": 0.8}
        )
        consensus = calculator.calculate(model_decisions)
    """
    
    def __init__(
        self,
        provider_weights: Optional[Dict[str, float]] = None,
        use_confidence_multiplier: bool = True,
        min_confidence_threshold: float = 0.5
    ):
        """
        Initialize weighted consensus calculator.
        
        Args:
            provider_weights: Weight for each provider (default: all 1.0)
            use_confidence_multiplier: Whether to multiply by confidence
            min_confidence_threshold: Minimum confidence to include decision
        """
        self.provider_weights = provider_weights or {
            "anthropic": 1.0,
            "openai": 1.0,
            "llama": 0.8  # Slightly lower weight for local model
        }
        self.use_confidence_multiplier = use_confidence_multiplier
        self.min_confidence_threshold = min_confidence_threshold
        
        logger.info(
            f"Initialized WeightedConsensusCalculator: "
            f"weights={self.provider_weights}, "
            f"confidence_multiplier={use_confidence_multiplier}"
        )
    
    def calculate(self, model_decisions: List[ModelDecision]) -> ConsensusAnalysis:
        """
        Calculate weighted consensus from model decisions.
        
        Args:
            model_decisions: List of decisions from different models
            
        Returns:
            ConsensusAnalysis with weighted results
        """
        if not model_decisions:
            raise ValueError("Cannot calculate consensus with no decisions")
        
        # Filter out low-confidence decisions
        valid_decisions = [
            d for d in model_decisions
            if d.confidence >= self.min_confidence_threshold
        ]
        
        if not valid_decisions:
            logger.warning(
                f"All decisions below confidence threshold "
                f"({self.min_confidence_threshold})"
            )
            valid_decisions = model_decisions  # Use all if none pass threshold
        
        # Calculate weighted votes
        weighted_votes: Dict[DecisionOutcome, float] = {}
        total_weight = 0.0
        
        for decision in valid_decisions:
            provider = decision.model_provider
            outcome = decision.decision
            
            # Get base weight for provider
            base_weight = self.provider_weights.get(provider, 1.0)
            
            # Apply confidence multiplier if enabled
            if self.use_confidence_multiplier:
                weight = base_weight * decision.confidence
            else:
                weight = base_weight
            
            # Add to weighted votes
            weighted_votes[outcome] = weighted_votes.get(outcome, 0.0) + weight
            total_weight += weight
            
            logger.debug(
                f"Decision from {provider}: {outcome.value} "
                f"(weight={weight:.3f}, confidence={decision.confidence:.2f})"
            )
        
        # Determine majority decision (highest weighted vote)
        majority_decision = max(weighted_votes, key=weighted_votes.get)
        majority_weight = weighted_votes[majority_decision]
        
        # Calculate agreement level (weighted)
        agreement_level = majority_weight / total_weight if total_weight > 0 else 0.0
        
        # Find dissenting models
        dissenting_models = [
            d.model_provider
            for d in valid_decisions
            if d.decision != majority_decision
        ]
        
        # Calculate confidence variance
        confidences = [d.confidence for d in valid_decisions]
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
        
        # Analyze reasoning divergence
        reasoning_divergence = self._analyze_reasoning_divergence(valid_decisions)
        
        consensus = ConsensusAnalysis(
            agreement_level=agreement_level,
            majority_decision=majority_decision,
            dissenting_models=dissenting_models,
            confidence_variance=variance,
            reasoning_divergence=reasoning_divergence
        )
        
        logger.info(
            f"Weighted consensus: {majority_decision.value} "
            f"(agreement={agreement_level:.2%}, variance={variance:.4f})"
        )
        
        return consensus
    
    def _analyze_reasoning_divergence(
        self,
        decisions: List[ModelDecision]
    ) -> Optional[str]:
        """
        Analyze if models reached same decision for different reasons.
        
        Args:
            decisions: List of model decisions
            
        Returns:
            Description of reasoning divergence, or None if consistent
        """
        # Group decisions by outcome
        by_outcome: Dict[DecisionOutcome, List[str]] = {}
        for decision in decisions:
            if decision.decision not in by_outcome:
                by_outcome[decision.decision] = []
            by_outcome[decision.decision].append(decision.reasoning)
        
        # Check for divergence within same outcome
        for outcome, reasonings in by_outcome.items():
            if len(reasonings) > 1:
                # Simple heuristic: check if key terms differ significantly
                # More sophisticated NLP analysis could be added here
                unique_terms = set()
                for reasoning in reasonings:
                    words = reasoning.lower().split()
                    unique_terms.update(words)
                
                if len(unique_terms) > 50:  # Arbitrary threshold
                    return (
                        f"Models agreeing on {outcome.value} used "
                        f"significantly different reasoning paths"
                    )
        
        return None


class SimpleMajorityCalculator:
    """
    Calculate consensus using simple majority voting.
    
    Each model gets one vote, regardless of confidence or provider.
    This is the baseline algorithm for comparison.
    """
    
    def calculate(self, model_decisions: List[ModelDecision]) -> ConsensusAnalysis:
        """
        Calculate simple majority consensus.
        
        Args:
            model_decisions: List of decisions from different models
            
        Returns:
            ConsensusAnalysis with majority results
        """
        if not model_decisions:
            raise ValueError("Cannot calculate consensus with no decisions")
        
        # Count votes
        vote_counts = Counter(d.decision for d in model_decisions)
        
        # Get majority decision
        majority_decision = vote_counts.most_common(1)[0][0]
        majority_count = vote_counts[majority_decision]
        
        # Calculate agreement level
        agreement_level = majority_count / len(model_decisions)
        
        # Find dissenting models
        dissenting_models = [
            d.model_provider
            for d in model_decisions
            if d.decision != majority_decision
        ]
        
        # Calculate confidence variance
        confidences = [d.confidence for d in model_decisions]
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
        
        return ConsensusAnalysis(
            agreement_level=agreement_level,
            majority_decision=majority_decision,
            dissenting_models=dissenting_models,
            confidence_variance=variance,
            reasoning_divergence=None
        )


def get_consensus_calculator(
    algorithm: ConsensusAlgorithm = ConsensusAlgorithm.WEIGHTED_VOTING,
    **kwargs
) -> Any:
    """
    Factory function to get consensus calculator.
    
    Args:
        algorithm: Which consensus algorithm to use
        **kwargs: Algorithm-specific configuration
        
    Returns:
        Consensus calculator instance
        
    Example:
        calculator = get_consensus_calculator(
            algorithm=ConsensusAlgorithm.WEIGHTED_VOTING,
            provider_weights={"anthropic": 1.0, "openai": 0.9}
        )
    """
    if algorithm == ConsensusAlgorithm.SIMPLE_MAJORITY:
        return SimpleMajorityCalculator()
    
    elif algorithm == ConsensusAlgorithm.WEIGHTED_VOTING:
        return WeightedConsensusCalculator(**kwargs)
    
    elif algorithm == ConsensusAlgorithm.CONFIDENCE_WEIGHTED:
        # Confidence-only weighting (no provider weights)
        return WeightedConsensusCalculator(
            provider_weights={},  # All providers equal
            use_confidence_multiplier=True,
            **kwargs
        )
    
    elif algorithm == ConsensusAlgorithm.BAYESIAN:
        raise NotImplementedError("Bayesian consensus not yet implemented")
    
    else:
        raise ValueError(f"Unknown consensus algorithm: {algorithm}")
