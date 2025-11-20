"""
Tests for fairness testing framework.
"""

import pytest
from services.fairness_testing import (
    CounterfactualFairnessTester,
    DemographicParityAnalyzer,
    IndividualFairnessTester,
    FairnessTestResult,
    get_fairness_tester
)
from models.decision import Decision, DecisionOutcome
from datetime import datetime


class TestDemographicParity:
    """Test demographic parity analysis."""
    
    @pytest.fixture
    def analyzer(self):
        """Create demographic parity analyzer."""
        return DemographicParityAnalyzer(max_disparity=0.2)
    
    def test_equal_approval_rates(self, analyzer):
        """Test that equal rates pass parity check."""
        decisions_by_group = {
            "group_a": ["approved", "approved", "denied"],
            "group_b": ["approved", "approved", "denied"]
        }
        
        result = analyzer.analyze(decisions_by_group)
        
        assert result.passed is True
        assert result.fairness_score > 0.9
        assert result.severity == "low"
    
    def test_high_disparity_fails(self, analyzer):
        """Test that high disparity fails parity check."""
        decisions_by_group = {
            "group_a": ["approved", "approved", "approved"],  # 100%
            "group_b": ["denied", "denied", "approved"]       # 33%
        }
        
        result = analyzer.analyze(decisions_by_group)
        
        assert result.passed is False
        assert result.details["disparity"] > 0.6
        assert result.severity in ["high", "critical"]
    
    def test_moderate_disparity(self, analyzer):
        """Test moderate disparity detection."""
        decisions_by_group = {
            "age_25-35": ["approved"] * 8 + ["denied"] * 2,  # 80%
            "age_55-65": ["approved"] * 6 + ["denied"] * 4   # 60%
        }
        
        result = analyzer.analyze(decisions_by_group)
        
        # 20% disparity is at threshold
        assert result.details["disparity"] == pytest.approx(0.2, abs=0.01)
    
    def test_empty_groups(self, analyzer):
        """Test handling of empty groups."""
        decisions_by_group = {}
        
        result = analyzer.analyze(decisions_by_group)
        
        assert result.passed is True  # No data = no violation


class TestIndividualFairness:
    """Test individual fairness."""
    
    @pytest.fixture
    def tester(self):
        """Create individual fairness tester."""
        return IndividualFairnessTester(similarity_threshold=0.9)
    
    def test_similarity_calculation(self, tester):
        """Test similarity calculation."""
        case1 = {"income": 50000, "credit_score": 700, "age": 30}
        case2 = {"income": 52000, "credit_score": 705, "age": 31}
        
        similarity = tester.calculate_similarity(case1, case2)
        
        assert similarity > 0.9  # Very similar cases
    
    def test_dissimilar_cases(self, tester):
        """Test dissimilar cases."""
        case1 = {"income": 50000, "credit_score": 700}
        case2 = {"income": 150000, "credit_score": 800}
        
        similarity = tester.calculate_similarity(case1, case2)
        
        assert similarity < 0.7  # Different cases
    
    def test_fair_treatment(self, tester):
        """Test that similar cases with same decision pass."""
        cases = [
            ({"income": 50000, "credit": 700}, "approved"),
            ({"income": 51000, "credit": 705}, "approved"),
            ({"income": 49000, "credit": 695}, "approved")
        ]
        
        result = tester.test_fairness(cases)
        
        assert result.passed is True
        assert result.fairness_score == 1.0
    
    def test_unfair_treatment(self, tester):
        """Test that similar cases with different decisions fail."""
        cases = [
            ({"income": 50000, "credit": 700}, "approved"),
            ({"income": 51000, "credit": 705}, "denied"),  # Very similar but denied
        ]
        
        result = tester.test_fairness(cases)
        
        assert result.passed is False
        assert len(result.details["violations"]) > 0


class TestFairnessFactory:
    """Test fairness tester factory."""
    
    def test_get_counterfactual_tester(self):
        """Test getting counterfactual tester."""
        tester = get_fairness_tester("counterfactual")
        assert isinstance(tester, CounterfactualFairnessTester)
    
    def test_get_demographic_parity(self):
        """Test getting demographic parity analyzer."""
        analyzer = get_fairness_tester("demographic_parity")
        assert isinstance(analyzer, DemographicParityAnalyzer)
    
    def test_get_individual_fairness(self):
        """Test getting individual fairness tester."""
        tester = get_fairness_tester("individual")
        assert isinstance(tester, IndividualFairnessTester)
    
    def test_unknown_type_raises(self):
        """Test that unknown type raises error."""
        with pytest.raises(ValueError):
            get_fairness_tester("unknown_type")


class TestContextualBias:
    """Test contextual bias detection."""
    
    def test_neutral_age_mention(self):
        """Test that neutral age mention is not flagged."""
        from services.contextual_bias import analyze_context
        
        text = "The applicant is 25 years old and has 3 years of experience."
        is_discriminatory, context = analyze_context(text, "25 years old")
        
        assert is_discriminatory is False
    
    def test_discriminatory_age_mention(self):
        """Test that discriminatory age mention is flagged."""
        from services.contextual_bias import analyze_context
        
        text = "The applicant is too young at 25 for this senior position."
        is_discriminatory, context = analyze_context(text, "young")
        
        assert is_discriminatory is True
    
    def test_bias_severity_calculation(self):
        """Test bias severity calculation."""
        from services.contextual_bias import calculate_bias_severity
        
        # Multiple attributes + high discrimination = critical
        severity = calculate_bias_severity(
            detected_attributes=["age", "race", "gender"],
            discriminatory_contexts=3,
            total_mentions=3
        )
        assert severity == "critical"
        
        # Single attribute + low discrimination = low
        severity = calculate_bias_severity(
            detected_attributes=["age"],
            discriminatory_contexts=0,
            total_mentions=1
        )
        assert severity == "low"
