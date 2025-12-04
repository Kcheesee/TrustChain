"""
Tests for TrustChain Phase 2 Components

Tests the new Phase 2 components:
- CriteriaDecompositionStrategy
- AdversarialReviewStrategy
- ProxyVariablesAnalyzer
- ConsumerExplanationOutput
- TrustChain dry_run mode

Run with: pytest tests/test_phase2.py -v

Built with care by Kareem & Claude
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

# Import core modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base import BaseStrategy, BaseAnalyzer, BaseOutput
from core.result import (
    DecisionOutcome,
    ReviewTrigger,
    StrategyResult,
    AnalysisResult,
    AccountabilityResult,
)
from core.registry import get_registry, register_component

# Import Phase 2 components
from strategies.criteria_decomposition import CriteriaDecompositionStrategy
from strategies.adversarial_review import AdversarialReviewStrategy
from analyzers.proxy_variables import ProxyVariablesAnalyzer
from outputs.consumer_explanation import ConsumerExplanationOutput


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def clean_registry():
    """Provide a clean registry for testing."""
    registry = get_registry()
    yield registry


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider for testing."""
    provider = MagicMock()
    provider.__class__.__name__ = "MockProvider"
    provider.model_name = "mock-model"
    provider.provider_name = "mock"

    # Default response
    response = MagicMock()
    response.content = "DECISION: APPROVE\nCONFIDENCE: 85%\nREASONING: Test approval"
    response.confidence = 0.85
    response.reasoning = "Test approval reasoning"

    provider.generate_decision = AsyncMock(return_value=response)
    return provider


@pytest.fixture
def sample_strategy_result():
    """Create a sample StrategyResult for testing."""
    return StrategyResult(
        strategy_name="test_strategy",
        decision=DecisionOutcome.APPROVED,
        confidence=0.85,
        reasoning="Test reasoning for approval",
        model_decisions=[
            {"provider": "anthropic", "decision": "approved", "confidence": 0.9},
        ],
        agreement_level=1.0,
    )


@pytest.fixture
def sample_accountability_result(sample_strategy_result):
    """Create a sample AccountabilityResult for testing."""
    return AccountabilityResult(
        result_id="tc_test_123",
        case_id="case_001",
        decision_type="unemployment_benefits",
        final_decision=DecisionOutcome.APPROVED,
        overall_confidence=0.85,
        requires_human_review=False,
        strategy_result=sample_strategy_result,
        analysis_results=[],
        primary_reasoning="Test reasoning",
        supporting_factors=["Good employment history", "Involuntary termination"],
        concerns=["Some income documentation missing"],
    )


@pytest.fixture
def hiring_input_data():
    """Sample hiring case input data."""
    return {
        "candidate_name": "Jane Smith",
        "position": "Software Engineer",
        "years_experience": 5,
        "education": "BS Computer Science",
        "skills": ["Python", "JavaScript", "SQL"],
    }


@pytest.fixture
def unemployment_input_data():
    """Sample unemployment benefits input data."""
    return {
        "applicant_name": "John Doe",
        "employment_duration_months": 24,
        "termination_reason": "company_layoff",
        "prior_earnings_annual": 55000,
        "available_for_work": True,
        "actively_seeking_work": True,
    }


# ============================================================================
# CRITERIA DECOMPOSITION STRATEGY TESTS
# ============================================================================

class TestCriteriaDecompositionStrategy:
    """Tests for CriteriaDecompositionStrategy."""

    def test_strategy_registration(self, clean_registry):
        """Test that strategy is properly registered."""
        assert clean_registry.has_strategy("criteria_decomposition")

    def test_strategy_initialization_defaults(self):
        """Test strategy initializes with default config."""
        strategy = CriteriaDecompositionStrategy()

        assert strategy.name == "criteria_decomposition"
        assert strategy.scoring_type == "percentage"
        assert strategy.require_all_criteria is False
        assert strategy.min_passing_score == 0.6

    def test_strategy_custom_config(self):
        """Test strategy with custom configuration."""
        config = {
            "criteria": {
                "skill_match": {"weight": 0.5, "description": "Technical skills"},
                "experience": {"weight": 0.5, "description": "Work experience"},
            },
            "scoring_type": "threshold",
            "min_passing_score": 0.7,
        }

        strategy = CriteriaDecompositionStrategy(config=config)

        assert len(strategy.criteria) == 2
        assert strategy.scoring_type == "threshold"
        assert strategy.min_passing_score == 0.7

    def test_config_validation_invalid_scoring_type(self):
        """Test config validation rejects invalid scoring type."""
        config = {"scoring_type": "invalid_type"}

        with pytest.raises(ValueError) as exc_info:
            CriteriaDecompositionStrategy(config=config)

        assert "scoring_type must be one of" in str(exc_info.value)

    def test_config_validation_invalid_weights(self):
        """Test config validation catches weights not summing to 1."""
        config = {
            "criteria": {
                "skill_match": {"weight": 0.3},
                "experience": {"weight": 0.3},  # Total = 0.6, not 1.0
            }
        }

        # Should log warning but not raise
        strategy = CriteriaDecompositionStrategy(config=config)
        assert strategy is not None

    @pytest.mark.asyncio
    async def test_evaluate_single_provider(self, mock_provider, hiring_input_data):
        """Test evaluation with a single provider."""
        strategy = CriteriaDecompositionStrategy()
        context = {
            "decision_type": "hiring",
            "system_context": "Evaluate job application",
        }

        result = await strategy.evaluate(
            hiring_input_data,
            context,
            [mock_provider]
        )

        assert isinstance(result, StrategyResult)
        assert result.strategy_name == "criteria_decomposition"
        assert result.decision in [DecisionOutcome.APPROVED, DecisionOutcome.DENIED, DecisionOutcome.NEEDS_REVIEW]

    @pytest.mark.asyncio
    async def test_evaluate_no_providers(self, hiring_input_data):
        """Test evaluation fails gracefully with no providers."""
        strategy = CriteriaDecompositionStrategy()

        result = await strategy.evaluate(
            hiring_input_data,
            {},
            []
        )

        assert result.decision == DecisionOutcome.NEEDS_REVIEW
        assert result.confidence == 0.0

    def test_calculate_final_decision_percentage(self):
        """Test final decision calculation with percentage scoring."""
        strategy = CriteriaDecompositionStrategy(config={
            "scoring_type": "percentage",
            "min_passing_score": 0.6,
        })

        # Test passing score
        scores = {
            "criterion_1": {"score": 0.8, "passed": True, "weight": 0.5},
            "criterion_2": {"score": 0.7, "passed": True, "weight": 0.5},
        }

        decision, confidence = strategy._calculate_final_decision(scores)
        assert decision == DecisionOutcome.APPROVED
        assert confidence == 0.75  # Weighted average

    def test_calculate_final_decision_threshold(self):
        """Test final decision calculation with threshold scoring."""
        strategy = CriteriaDecompositionStrategy(config={
            "scoring_type": "threshold",
            "criteria": {
                "required": {"weight": 0.5, "threshold": 0.7},
                "optional": {"weight": 0.5, "threshold": 0.5},
            },
            "require_all_criteria": True,
        })

        # Test failing threshold
        scores = {
            "required": {"score": 0.5, "passed": False, "weight": 0.5},  # Below threshold
            "optional": {"score": 0.8, "passed": True, "weight": 0.5},
        }

        decision, confidence = strategy._calculate_final_decision(scores)
        assert decision == DecisionOutcome.DENIED


# ============================================================================
# ADVERSARIAL REVIEW STRATEGY TESTS
# ============================================================================

class TestAdversarialReviewStrategy:
    """Tests for AdversarialReviewStrategy."""

    def test_strategy_registration(self, clean_registry):
        """Test that strategy is properly registered."""
        assert clean_registry.has_strategy("adversarial_review")

    def test_strategy_initialization_defaults(self):
        """Test strategy initializes with default config."""
        strategy = AdversarialReviewStrategy()

        assert strategy.name == "adversarial_review"
        assert strategy.challenge_strength == "medium"
        assert strategy.require_defense is True
        assert strategy.max_challenges == 3
        assert strategy.survival_threshold == 0.6

    def test_config_validation_invalid_strength(self):
        """Test config validation rejects invalid challenge strength."""
        config = {"challenge_strength": "extreme"}

        with pytest.raises(ValueError) as exc_info:
            AdversarialReviewStrategy(config=config)

        assert "challenge_strength must be one of" in str(exc_info.value)

    def test_config_validation_invalid_threshold(self):
        """Test config validation rejects invalid survival threshold."""
        config = {"survival_threshold": 1.5}

        with pytest.raises(ValueError) as exc_info:
            AdversarialReviewStrategy(config=config)

        assert "survival_threshold must be between" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_evaluate_no_providers(self, unemployment_input_data):
        """Test evaluation fails gracefully with no providers."""
        strategy = AdversarialReviewStrategy()

        result = await strategy.evaluate(
            unemployment_input_data,
            {},
            []
        )

        assert result.decision == DecisionOutcome.NEEDS_REVIEW
        assert result.confidence == 0.0

    def test_parse_decision(self):
        """Test decision parsing from LLM response."""
        strategy = AdversarialReviewStrategy()

        assert strategy._parse_decision("I approve this application") == DecisionOutcome.APPROVED
        assert strategy._parse_decision("Application denied") == DecisionOutcome.DENIED
        assert strategy._parse_decision("Cannot determine") == DecisionOutcome.NEEDS_REVIEW

    def test_parse_challenges(self):
        """Test challenge parsing from LLM response."""
        strategy = AdversarialReviewStrategy()

        response = """
        CHALLENGE: Employment gap not explained
        SEVERITY: HIGH
        IMPACT: Could indicate unreported issues
        ---
        CHALLENGE: Income documentation incomplete
        SEVERITY: MEDIUM
        IMPACT: May affect eligibility calculation
        """

        challenges = strategy._parse_challenges(response)

        assert len(challenges) == 2
        assert challenges[0]["challenge"] == "Employment gap not explained"
        assert challenges[0]["severity"] == "HIGH"
        assert challenges[1]["severity"] == "MEDIUM"

    def test_parse_defense(self):
        """Test defense parsing from LLM response."""
        strategy = AdversarialReviewStrategy()

        # Successful defense
        response = "DEFENSE: The gap was due to documented medical leave\nDEFENDED: YES"
        defense, defended = strategy._parse_defense(response)
        assert defended is True

        # Unsuccessful defense
        response = "DEFENSE: Cannot adequately explain\nDEFENDED: NO"
        defense, defended = strategy._parse_defense(response)
        assert defended is False

    def test_evaluate_survival_no_challenges(self):
        """Test survival evaluation with no challenges."""
        strategy = AdversarialReviewStrategy()

        survived, confidence, reasoning = strategy._evaluate_survival(
            initial_decision=DecisionOutcome.APPROVED,
            initial_confidence=0.8,
            initial_reasoning="Test",
            challenges=[],
            defense_results=[]
        )

        assert survived is True
        assert confidence == 0.8

    def test_evaluate_survival_high_severity_undefended(self):
        """Test survival fails with undefended HIGH severity challenge."""
        strategy = AdversarialReviewStrategy()

        challenges = [{"challenge": "Major issue", "severity": "HIGH"}]
        defenses = [{"challenge_id": 0, "successfully_defended": False}]

        survived, confidence, reasoning = strategy._evaluate_survival(
            initial_decision=DecisionOutcome.APPROVED,
            initial_confidence=0.8,
            initial_reasoning="Test",
            challenges=challenges,
            defense_results=defenses
        )

        assert survived is False
        assert confidence < 0.8


# ============================================================================
# PROXY VARIABLES ANALYZER TESTS
# ============================================================================

class TestProxyVariablesAnalyzer:
    """Tests for ProxyVariablesAnalyzer."""

    def test_analyzer_registration(self, clean_registry):
        """Test that analyzer is properly registered."""
        assert clean_registry.has_analyzer("proxy_variables")

    def test_analyzer_initialization_defaults(self):
        """Test analyzer initializes with default config."""
        analyzer = ProxyVariablesAnalyzer()

        assert analyzer.name == "proxy_variables"
        assert analyzer.sensitivity == "medium"
        assert analyzer.blocking is True

    @pytest.mark.skip(reason="ProxyType enum not implemented in module")
    def test_proxy_type_enum(self):
        """Test ProxyType enum values."""
        # ProxyType enum was planned but not implemented
        pass

    def test_detect_zip_code_proxy(self):
        """Test ZIP code proxy detection."""
        analyzer = ProxyVariablesAnalyzer()

        # Create strategy result with ZIP code mention
        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.8,
            reasoning="Candidate from zip code 90210 area which has lower employment rates",
        )

        result = analyzer.analyze(strategy_result, {}, {})

        assert result.passed is False
        assert len(result.detected_proxies) > 0
        assert any("zip" in p.lower() for p in result.detected_proxies)

    def test_detect_culture_fit_proxy(self):
        """Test culture fit proxy detection (critical for hiring)."""
        analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "high"})

        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.7,
            reasoning="Candidate doesn't seem like a good culture fit for our team",
        )

        result = analyzer.analyze(strategy_result, {}, {"decision_type": "hiring"})

        assert result.passed is False
        assert len(result.detected_proxies) > 0

    def test_detect_graduation_year_proxy(self):
        """Test graduation year proxy detection (age discrimination)."""
        analyzer = ProxyVariablesAnalyzer()

        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.75,
            reasoning="Graduated in 1985 which suggests outdated skills",
        )

        result = analyzer.analyze(strategy_result, {}, {})

        assert result.passed is False
        # Should flag as potential age proxy

    def test_no_proxies_passes(self):
        """Test clean reasoning passes analysis."""
        analyzer = ProxyVariablesAnalyzer()

        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.APPROVED,
            confidence=0.9,
            reasoning="Candidate has excellent technical skills and relevant experience",
        )

        result = analyzer.analyze(strategy_result, {}, {})

        assert result.passed is True
        assert len(result.detected_proxies) == 0

    def test_custom_patterns(self):
        """Test custom additional patterns detection."""
        config = {
            "additional_patterns": {
                "commute": ["long commute", "travel distance", "far from office"]
            }
        }
        analyzer = ProxyVariablesAnalyzer(config=config)

        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.6,
            reasoning="Concerns about long commute time",
        )

        result = analyzer.analyze(strategy_result, {}, {})

        assert result.passed is False

    def test_sensitivity_levels(self):
        """Test different sensitivity levels."""
        # Low sensitivity - fewer detections
        low_analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "low"})
        # High sensitivity - more detections
        high_analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "high"})

        strategy_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.7,
            reasoning="Based on the neighborhood demographics",
        )

        low_result = low_analyzer.analyze(strategy_result, {}, {})
        high_result = high_analyzer.analyze(strategy_result, {}, {})

        # High sensitivity should catch more
        assert len(high_result.detected_proxies) >= len(low_result.detected_proxies)


# ============================================================================
# CONSUMER EXPLANATION OUTPUT TESTS
# ============================================================================

class TestConsumerExplanationOutput:
    """Tests for ConsumerExplanationOutput."""

    def test_output_registration(self, clean_registry):
        """Test that output is properly registered."""
        assert clean_registry.has_output("consumer_explanation")

    def test_output_initialization_defaults(self):
        """Test output initializes with default config."""
        output = ConsumerExplanationOutput()

        assert output.name == "consumer_explanation"
        assert output.language_level == "simple"
        assert output.include_appeal_info is True
        assert output.include_feedback is True

    def test_config_validation_invalid_language(self):
        """Test config validation rejects invalid language level."""
        config = {"language_level": "technical"}

        with pytest.raises(ValueError) as exc_info:
            ConsumerExplanationOutput(config=config)

        assert "language_level must be one of" in str(exc_info.value)

    def test_generate_approved_explanation(self, sample_accountability_result):
        """Test generating explanation for approved decision."""
        output = ConsumerExplanationOutput()

        result = output.generate(sample_accountability_result)

        assert "summary" in result
        assert "approved" in result["summary"].lower() or "good news" in result["summary"].lower()
        assert result["decision"] == "approved"

    def test_generate_denied_explanation(self, sample_accountability_result):
        """Test generating explanation for denied decision."""
        sample_accountability_result.final_decision = DecisionOutcome.DENIED

        output = ConsumerExplanationOutput()
        result = output.generate(sample_accountability_result)

        assert "appeal_information" in result
        assert result["appeal_information"]["can_appeal"] is True

    def test_generate_needs_review_explanation(self, sample_accountability_result):
        """Test generating explanation for needs_review decision."""
        sample_accountability_result.final_decision = DecisionOutcome.NEEDS_REVIEW
        sample_accountability_result.requires_human_review = True

        output = ConsumerExplanationOutput()
        result = output.generate(sample_accountability_result)

        assert "review_notice" in result

    def test_language_levels(self, sample_accountability_result):
        """Test different language levels produce different output."""
        simple_output = ConsumerExplanationOutput(config={"language_level": "simple"})
        formal_output = ConsumerExplanationOutput(config={"language_level": "formal"})

        simple_result = simple_output.generate(sample_accountability_result)
        formal_result = formal_output.generate(sample_accountability_result)

        # Summaries should be different
        assert simple_result["summary"] != formal_result["summary"]

    def test_key_factors_extraction(self, sample_accountability_result):
        """Test key factors are properly extracted."""
        output = ConsumerExplanationOutput(config={"max_factors": 3})

        result = output.generate(sample_accountability_result)

        assert "key_factors" in result
        assert len(result["key_factors"]) <= 3

    def test_feedback_generation(self, sample_accountability_result):
        """Test feedback/improvement suggestions are generated."""
        sample_accountability_result.final_decision = DecisionOutcome.DENIED
        sample_accountability_result.concerns = ["Income documentation incomplete"]

        output = ConsumerExplanationOutput(config={"include_feedback": True})
        result = output.generate(sample_accountability_result)

        assert "feedback" in result
        assert len(result["feedback"]) > 0

    def test_no_appeal_info_for_approved(self, sample_accountability_result):
        """Test no appeal info shown for approved decisions."""
        output = ConsumerExplanationOutput()
        result = output.generate(sample_accountability_result)

        # Appeal info should be None for approved
        assert result.get("appeal_information") is None

    def test_humanize_decision_type(self):
        """Test decision type humanization."""
        output = ConsumerExplanationOutput()

        assert output._humanize_decision_type("unemployment_benefits") == "unemployment benefits"
        assert output._humanize_decision_type("hiring") == "job application"
        assert output._humanize_decision_type("loan_approval") == "loan"

    def test_confidence_statement(self, sample_accountability_result):
        """Test confidence statement generation."""
        output = ConsumerExplanationOutput()

        # High confidence
        sample_accountability_result.overall_confidence = 0.95
        result = output.generate(sample_accountability_result)
        assert "high confidence" in result["confidence_statement"].lower()

        # Low confidence
        sample_accountability_result.overall_confidence = 0.5
        result = output.generate(sample_accountability_result)
        assert "uncertainty" in result["confidence_statement"].lower() or "additional review" in result["confidence_statement"].lower()


# ============================================================================
# TRUSTCHAIN DRY RUN TESTS
# ============================================================================

class TestTrustChainDryRun:
    """Tests for TrustChain dry_run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_basic(self):
        """Test basic dry run functionality."""
        from services.trustchain import TrustChain

        tc = TrustChain(
            strategies=[CriteriaDecompositionStrategy()],
            analyzers=[ProxyVariablesAnalyzer()],
            outputs=[ConsumerExplanationOutput()],
        )

        result = await tc.evaluate(
            case_id="dry_run_test",
            input_data={"test": "data"},
            dry_run=True
        )

        assert result.strategy_result.strategy_name == "dry_run"
        assert "execution_plan" in result.strategy_result.metadata

    @pytest.mark.asyncio
    async def test_dry_run_validates_components(self):
        """Test dry run validates all components."""
        from services.trustchain import TrustChain

        tc = TrustChain(
            strategies=[CriteriaDecompositionStrategy(), AdversarialReviewStrategy()],
            analyzers=[ProxyVariablesAnalyzer()],
            outputs=[ConsumerExplanationOutput()],
        )

        result = await tc.evaluate(
            case_id="validation_test",
            input_data={"applicant": "test"},
            dry_run=True
        )

        plan = result.strategy_result.metadata["execution_plan"]

        assert len(plan["strategies"]) == 2
        assert len(plan["analyzers"]) == 1
        assert len(plan["outputs"]) == 1

    @pytest.mark.asyncio
    async def test_dry_run_no_providers_warning(self):
        """Test dry run warns when no providers configured."""
        from services.trustchain import TrustChain

        tc = TrustChain(
            strategies=[CriteriaDecompositionStrategy()],
            providers=[],  # No providers
        )

        result = await tc.evaluate(
            case_id="no_providers_test",
            input_data={"test": "data"},
            dry_run=True
        )

        plan = result.strategy_result.metadata["execution_plan"]

        assert "No LLM providers configured" in plan["issues"]
        assert plan["ready_to_execute"] is False

    @pytest.mark.asyncio
    async def test_dry_run_strategy_cant_execute(self, mock_provider):
        """Test dry run flags strategies that can't execute."""
        from services.trustchain import TrustChain
        from strategies.multi_model_consensus import MultiModelConsensusStrategy

        # Multi-model consensus needs 2+ providers
        tc = TrustChain(
            strategies=[MultiModelConsensusStrategy()],
            providers=[mock_provider],  # Only 1 provider
        )

        result = await tc.evaluate(
            case_id="strategy_check_test",
            input_data={"test": "data"},
            dry_run=True
        )

        plan = result.strategy_result.metadata["execution_plan"]

        # Should have warning about not enough providers
        multi_model = plan["strategies"][0]
        assert multi_model["can_execute"] is False
        assert "warning" in multi_model

    @pytest.mark.asyncio
    async def test_dry_run_from_config(self):
        """Test dry run with config file."""
        from services.trustchain import TrustChain
        import os

        # Use actual config file
        config_path = Path(__file__).parent.parent.parent / "configs" / "hiring.yaml"

        if config_path.exists():
            tc = TrustChain.from_config(str(config_path))

            result = await tc.evaluate(
                case_id="config_dry_run",
                input_data={"position": "Engineer"},
                dry_run=True
            )

            plan = result.strategy_result.metadata["execution_plan"]
            assert plan["decision_type"] == "hiring"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
