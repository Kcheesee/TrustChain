"""
Unit tests for consensus algorithms.

Tests weighted voting, simple majority, and consensus quality metrics.
"""

import pytest
from services.consensus_algorithms import (
    WeightedConsensusCalculator,
    SimpleMajorityCalculator,
    ConsensusAlgorithm,
    get_consensus_calculator
)
from models.decision import ModelDecision, DecisionOutcome
from datetime import datetime


class TestWeightedConsensus:
    """Test weighted consensus algorithm."""
    
    @pytest.fixture
    def calculator(self):
        """Create weighted consensus calculator."""
        return WeightedConsensusCalculator(
            provider_weights={
                "anthropic": 1.0,
                "openai": 1.0,
                "llama": 0.8
            },
            use_confidence_multiplier=True
        )
    
    def test_unanimous_high_confidence(self, calculator):
        """Test unanimous decision with high confidence."""
        decisions = [
            ModelDecision(
                model_provider="anthropic",
                model_name="claude-3-opus",
                decision=DecisionOutcome.APPROVED,
                reasoning="Strong qualifications",
                confidence=0.95
            ),
            ModelDecision(
                model_provider="openai",
                model_name="gpt-4",
                decision=DecisionOutcome.APPROVED,
                reasoning="Meets all criteria",
                confidence=0.92
            ),
            ModelDecision(
                model_provider="llama",
                model_name="llama-3-70b",
                decision=DecisionOutcome.APPROVED,
                reasoning="Eligible",
                confidence=0.88
            )
        ]
        
        consensus = calculator.calculate(decisions)
        
        assert consensus.majority_decision == DecisionOutcome.APPROVED
        assert consensus.agreement_level > 0.95  # Should be very high
        assert len(consensus.dissenting_models) == 0
        assert consensus.confidence_variance < 0.01  # Low variance
    
    def test_weighted_majority_wins(self, calculator):
        """Test that weighted votes determine winner."""
        decisions = [
            # Anthropic and OpenAI vote APPROVED (weight 1.0 each)
            ModelDecision(
                model_provider="anthropic",
                model_name="claude",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.9
            ),
            ModelDecision(
                model_provider="openai",
                model_name="gpt-4",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.9
            ),
            # Llama votes DENIED (weight 0.8)
            ModelDecision(
                model_provider="llama",
                model_name="llama-3",
                decision=DecisionOutcome.DENIED,
                reasoning="Risky",
                confidence=0.9
            )
        ]
        
        consensus = calculator.calculate(decisions)
        
        # APPROVED should win due to higher combined weight
        assert consensus.majority_decision == DecisionOutcome.APPROVED
        assert "llama" in consensus.dissenting_models
    
    def test_confidence_multiplier_effect(self, calculator):
        """Test that confidence affects vote weight."""
        decisions = [
            # High confidence APPROVED
            ModelDecision(
                model_provider="anthropic",
                model_name="claude",
                decision=DecisionOutcome.APPROVED,
                reasoning="Very confident",
                confidence=0.95
            ),
            # Low confidence DENIED (should have less weight)
            ModelDecision(
                model_provider="openai",
                model_name="gpt-4",
                decision=DecisionOutcome.DENIED,
                reasoning="Uncertain",
                confidence=0.55
            )
        ]
        
        consensus = calculator.calculate(decisions)
        
        # APPROVED should win due to higher confidence
        assert consensus.majority_decision == DecisionOutcome.APPROVED
    
    def test_low_confidence_filtering(self):
        """Test that very low confidence decisions are filtered."""
        calculator = WeightedConsensusCalculator(
            min_confidence_threshold=0.6
        )
        
        decisions = [
            ModelDecision(
                model_provider="anthropic",
                model_name="claude",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.8
            ),
            ModelDecision(
                model_provider="openai",
                model_name="gpt-4",
                decision=DecisionOutcome.DENIED,
                reasoning="Uncertain",
                confidence=0.4  # Below threshold
            )
        ]
        
        consensus = calculator.calculate(decisions)
        
        # Only high-confidence decision should count
        assert consensus.majority_decision == DecisionOutcome.APPROVED


class TestSimpleMajority:
    """Test simple majority algorithm."""
    
    @pytest.fixture
    def calculator(self):
        """Create simple majority calculator."""
        return SimpleMajorityCalculator()
    
    def test_simple_majority(self, calculator):
        """Test basic majority voting."""
        decisions = [
            ModelDecision(
                model_provider="anthropic",
                model_name="claude",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.9
            ),
            ModelDecision(
                model_provider="openai",
                model_name="gpt-4",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.5  # Low confidence doesn't matter
            ),
            ModelDecision(
                model_provider="llama",
                model_name="llama-3",
                decision=DecisionOutcome.DENIED,
                reasoning="Bad",
                confidence=0.95  # High confidence doesn't matter
            )
        ]
        
        consensus = calculator.calculate(decisions)
        
        # 2 out of 3 vote APPROVED
        assert consensus.majority_decision == DecisionOutcome.APPROVED
        assert consensus.agreement_level == 2/3
        assert "llama" in consensus.dissenting_models


class TestConsensusFactory:
    """Test consensus calculator factory."""
    
    def test_get_simple_majority(self):
        """Test getting simple majority calculator."""
        calc = get_consensus_calculator(ConsensusAlgorithm.SIMPLE_MAJORITY)
        assert isinstance(calc, SimpleMajorityCalculator)
    
    def test_get_weighted_voting(self):
        """Test getting weighted voting calculator."""
        calc = get_consensus_calculator(
            ConsensusAlgorithm.WEIGHTED_VOTING,
            provider_weights={"anthropic": 1.0}
        )
        assert isinstance(calc, WeightedConsensusCalculator)
    
    def test_get_confidence_weighted(self):
        """Test getting confidence-weighted calculator."""
        calc = get_consensus_calculator(ConsensusAlgorithm.CONFIDENCE_WEIGHTED)
        assert isinstance(calc, WeightedConsensusCalculator)
        assert calc.use_confidence_multiplier is True
    
    def test_unknown_algorithm_raises(self):
        """Test that unknown algorithm raises error."""
        with pytest.raises(ValueError):
            get_consensus_calculator("unknown_algorithm")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_decisions_raises(self):
        """Test that empty decision list raises error."""
        calc = WeightedConsensusCalculator()
        
        with pytest.raises(ValueError, match="no decisions"):
            calc.calculate([])
    
    def test_single_decision(self):
        """Test consensus with single decision."""
        calc = WeightedConsensusCalculator()
        
        decisions = [
            ModelDecision(
                model_provider="anthropic",
                model_name="claude",
                decision=DecisionOutcome.APPROVED,
                reasoning="Good",
                confidence=0.9
            )
        ]
        
        consensus = calc.calculate(decisions)
        
        assert consensus.majority_decision == DecisionOutcome.APPROVED
        assert consensus.agreement_level == 1.0
        assert len(consensus.dissenting_models) == 0
