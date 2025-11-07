"""
Unit tests for bias detection system
"""
import pytest
from services.bias_detection import BiasDetector
from models.decision import ModelDecision, ConsensusDecision


class TestBiasDetector:
    """Test suite for BiasDetector class"""

    @pytest.fixture
    def detector(self):
        """Create a BiasDetector instance"""
        return BiasDetector()

    def test_protected_attribute_detection_race(self, detector):
        """Test detection of race-related protected attributes"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude-opus-4",
                decision="approve",
                reasoning="The applicant is Black and has good credit.",
                confidence=0.9
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_001", "loan", "standard")

        assert result.bias_detected is True
        assert "race" in result.protected_attributes_found
        assert result.requires_human_review is True

    def test_protected_attribute_detection_age(self, detector):
        """Test detection of age-related protected attributes"""
        decisions = [
            ModelDecision(
                provider="openai",
                model="gpt-4",
                decision="deny",
                reasoning="The applicant is 65 years old and may not be suitable.",
                confidence=0.85
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="deny",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_002", "employment", "standard")

        assert result.bias_detected is True
        assert "age" in result.protected_attributes_found or "older" in result.protected_attributes_found
        assert result.requires_human_review is True

    def test_protected_attribute_detection_gender(self, detector):
        """Test detection of gender-related protected attributes"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude-sonnet",
                decision="approve",
                reasoning="She is a qualified female candidate for this position.",
                confidence=0.9
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_003", "hiring", "standard")

        assert result.bias_detected is True
        assert any(attr in result.protected_attributes_found for attr in ["gender", "female"])
        assert result.requires_human_review is True

    def test_no_bias_clean_reasoning(self, detector):
        """Test that clean reasoning doesn't trigger bias detection"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude-opus",
                decision="approve",
                reasoning="Applicant has 5 years experience, good credit score of 750, stable income, and no prior defaults.",
                confidence=0.95
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_004", "loan", "standard")

        assert result.bias_detected is False
        assert len(result.protected_attributes_found) == 0
        assert result.requires_human_review is False

    def test_low_confidence_triggers_review(self, detector):
        """Test that low confidence triggers human review"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude",
                decision="approve",
                reasoning="This is a borderline case with mixed signals.",
                confidence=0.55  # Below 0.7 threshold
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_005", "loan", "standard")

        # Low confidence should trigger review
        assert result.requires_human_review is True
        assert "low_confidence" in [t.lower().replace(" ", "_") for t in result.safety_triggers]

    def test_low_consensus_triggers_review(self, detector):
        """Test that low consensus triggers human review"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude",
                decision="approve",
                reasoning="Good application",
                confidence=0.9
            ),
            ModelDecision(
                provider="openai",
                model="gpt-4",
                decision="deny",
                reasoning="Risky application",
                confidence=0.85
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=0.5,  # 50% consensus (low)
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_006", "loan", "standard")

        assert result.requires_human_review is True
        assert any("consensus" in t.lower() for t in result.safety_triggers)

    def test_critical_decision_always_requires_review(self, detector):
        """Test that critical decisions always require human review"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude",
                decision="deny",
                reasoning="Insufficient documentation provided.",
                confidence=0.95
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="deny",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_007", "deportation", "critical")

        # Critical decision types always require review
        assert result.requires_human_review is True
        assert any("critical" in t.lower() or "deportation" in t.lower() for t in result.safety_triggers)

    def test_multiple_protected_attributes(self, detector):
        """Test detection of multiple protected attributes"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude",
                decision="approve",
                reasoning="The 55-year-old Muslim woman from Syria has good qualifications despite her disability.",
                confidence=0.9
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="approve",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_008", "visa", "high_stakes")

        assert result.bias_detected is True
        # Should detect age, religion, gender, national origin, disability
        assert len(result.protected_attributes_found) >= 3
        assert result.requires_human_review is True

    def test_high_stakes_benefit_termination(self, detector):
        """Test that benefit termination triggers review"""
        decisions = [
            ModelDecision(
                provider="anthropic",
                model="claude",
                decision="deny",
                reasoning="Applicant no longer meets eligibility requirements.",
                confidence=0.9
            )
        ]

        consensus = ConsensusDecision(
            consensus_level=1.0,
            final_decision="deny",
            model_decisions=decisions
        )

        result = detector.analyze_for_bias(consensus, "test_case_009", "unemployment_benefits", "high_stakes")

        # Denying benefits in high-stakes should trigger review
        assert result.requires_human_review is True
        assert any("benefit" in t.lower() for t in result.safety_triggers)
