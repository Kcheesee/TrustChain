"""
Tests for TrustChain Core Abstractions

Tests the plugin architecture components:
- Base classes
- Result objects
- Component registry
- Configuration system

Run with: pytest tests/test_core.py -v
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List

# Import core modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base import (
    ComponentType,
    BaseComponent,
    BaseStrategy,
    BaseAnalyzer,
    BaseOutput,
)
from core.result import (
    DecisionOutcome,
    ReviewTrigger,
    StrategyResult,
    AnalysisResult,
    AccountabilityResult,
)
from core.registry import (
    ComponentRegistry,
    get_registry,
    register_component,
)
from core.config import (
    StrategyConfig,
    AnalyzerConfig,
    OutputConfig,
    TrustChainConfig,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

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
            {"provider": "openai", "decision": "approved", "confidence": 0.8},
        ],
        agreement_level=1.0,
    )


@pytest.fixture
def sample_analysis_result():
    """Create a sample AnalysisResult for testing."""
    return AnalysisResult(
        analyzer_name="test_analyzer",
        passed=True,
        flags=[],
        warnings=["Minor concern"],
        recommendation="Proceed with caution",
    )


@pytest.fixture
def sample_accountability_result(sample_strategy_result, sample_analysis_result):
    """Create a sample AccountabilityResult for testing."""
    return AccountabilityResult(
        result_id="tc_test_123",
        case_id="case_001",
        decision_type="test_decision",
        final_decision=DecisionOutcome.APPROVED,
        overall_confidence=0.85,
        requires_human_review=False,
        strategy_result=sample_strategy_result,
        analysis_results=[sample_analysis_result],
        primary_reasoning="Test reasoning",
    )


@pytest.fixture
def clean_registry():
    """Provide a clean registry for testing."""
    registry = get_registry()
    registry.clear()
    yield registry
    registry.clear()


# ============================================================================
# BASE CLASSES TESTS
# ============================================================================

class TestBaseClasses:
    """Tests for base component classes."""

    def test_component_type_enum(self):
        """Test ComponentType enum values."""
        assert ComponentType.STRATEGY.value == "strategy"
        assert ComponentType.ANALYZER.value == "analyzer"
        assert ComponentType.OUTPUT.value == "output"

    def test_base_strategy_metadata(self, clean_registry):
        """Test BaseStrategy metadata property."""
        class TestStrategy(BaseStrategy):
            name = "test_strategy"
            description = "A test strategy"
            version = "1.0.0"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        strategy = TestStrategy()
        metadata = strategy.metadata

        assert metadata["name"] == "test_strategy"
        assert metadata["type"] == "strategy"
        assert metadata["description"] == "A test strategy"
        assert metadata["version"] == "1.0.0"

    def test_base_analyzer_blocking_default(self, clean_registry):
        """Test BaseAnalyzer default blocking attribute."""
        class TestAnalyzer(BaseAnalyzer):
            name = "test_analyzer"
            description = "A test analyzer"

            def validate_config(self, config):
                return True

            def analyze(self, strategy_result, input_data, context):
                pass

        analyzer = TestAnalyzer()
        assert analyzer.blocking is True

    def test_base_output_format_default(self, clean_registry):
        """Test BaseOutput default output_format attribute."""
        class TestOutput(BaseOutput):
            name = "test_output"
            description = "A test output"

            def validate_config(self, config):
                return True

            def generate(self, accountability_result):
                pass

        output = TestOutput()
        assert output.output_format == "json"


# ============================================================================
# RESULT OBJECTS TESTS
# ============================================================================

class TestResultObjects:
    """Tests for result object classes."""

    def test_decision_outcome_enum(self):
        """Test DecisionOutcome enum values."""
        assert DecisionOutcome.APPROVED.value == "approved"
        assert DecisionOutcome.DENIED.value == "denied"
        assert DecisionOutcome.NEEDS_REVIEW.value == "needs_review"

    def test_review_trigger_enum(self):
        """Test ReviewTrigger enum values."""
        assert ReviewTrigger.LOW_CONFIDENCE.value == "low_confidence"
        assert ReviewTrigger.BIAS_DETECTED.value == "bias_detected"

    def test_strategy_result_to_dict(self, sample_strategy_result):
        """Test StrategyResult serialization."""
        result_dict = sample_strategy_result.to_dict()

        assert result_dict["strategy_name"] == "test_strategy"
        assert result_dict["decision"] == "approved"
        assert result_dict["confidence"] == 0.85
        assert len(result_dict["model_decisions"]) == 2

    def test_analysis_result_to_dict(self, sample_analysis_result):
        """Test AnalysisResult serialization."""
        result_dict = sample_analysis_result.to_dict()

        assert result_dict["analyzer_name"] == "test_analyzer"
        assert result_dict["passed"] is True
        assert result_dict["warnings"] == ["Minor concern"]

    def test_accountability_result_audit_hash(self, sample_accountability_result):
        """Test audit hash generation."""
        # Calculate hash
        hash1 = sample_accountability_result.calculate_audit_hash()
        assert len(hash1) == 64  # SHA-256 hex string

        # Hash should be deterministic
        hash2 = sample_accountability_result.calculate_audit_hash()
        assert hash1 == hash2

    def test_accountability_result_finalize(self, sample_accountability_result):
        """Test result finalization."""
        input_data = {"field1": "value1", "field2": "value2"}
        sample_accountability_result.finalize(input_data)

        assert sample_accountability_result.audit_hash != ""
        assert sample_accountability_result.input_data_hash != ""

    def test_accountability_result_verify_integrity(self, sample_accountability_result):
        """Test integrity verification."""
        sample_accountability_result.finalize({"test": "data"})

        # Should pass verification
        assert sample_accountability_result.verify_integrity() is True

        # Modify result
        sample_accountability_result.overall_confidence = 0.5

        # Should fail verification
        assert sample_accountability_result.verify_integrity() is False

    def test_accountability_result_to_foia_report(self, sample_accountability_result):
        """Test FOIA report generation."""
        sample_accountability_result.finalize({"test": "data"})
        foia = sample_accountability_result.to_foia_report()

        # Should include key fields
        assert "result_id" in foia
        assert "case_id" in foia
        assert "final_decision" in foia
        assert "primary_reasoning" in foia

        # Should exclude internal details
        assert "config_snapshot" not in foia


# ============================================================================
# REGISTRY TESTS
# ============================================================================

class TestComponentRegistry:
    """Tests for ComponentRegistry."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_register_strategy(self, clean_registry):
        """Test registering a strategy."""
        class TestStrategy(BaseStrategy):
            name = "test_strategy"
            description = "Test"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        clean_registry.register(TestStrategy)
        assert clean_registry.has_strategy("test_strategy")

    def test_register_analyzer(self, clean_registry):
        """Test registering an analyzer."""
        class TestAnalyzer(BaseAnalyzer):
            name = "test_analyzer"
            description = "Test"

            def validate_config(self, config):
                return True

            def analyze(self, strategy_result, input_data, context):
                pass

        clean_registry.register(TestAnalyzer)
        assert clean_registry.has_analyzer("test_analyzer")

    def test_register_output(self, clean_registry):
        """Test registering an output generator."""
        class TestOutput(BaseOutput):
            name = "test_output"
            description = "Test"

            def validate_config(self, config):
                return True

            def generate(self, accountability_result):
                return {}

        clean_registry.register(TestOutput)
        assert clean_registry.has_output("test_output")

    def test_get_strategy_instance(self, clean_registry):
        """Test getting a strategy instance."""
        class TestStrategy(BaseStrategy):
            name = "test_strategy"
            description = "Test"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        clean_registry.register(TestStrategy)
        strategy = clean_registry.get_strategy("test_strategy", {"key": "value"})

        assert strategy.name == "test_strategy"
        assert strategy.config == {"key": "value"}

    def test_get_unknown_component_raises(self, clean_registry):
        """Test that getting unknown component raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            clean_registry.get_strategy("nonexistent")

        assert "Unknown strategy" in str(exc_info.value)

    def test_list_components(self, clean_registry):
        """Test listing registered components."""
        class TestStrategy(BaseStrategy):
            name = "test_strategy"
            description = "Test"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        clean_registry.register(TestStrategy)
        components = clean_registry.list_components()

        assert "test_strategy" in components["strategies"]

    def test_register_component_decorator(self, clean_registry):
        """Test the @register_component decorator."""
        @register_component
        class DecoratedStrategy(BaseStrategy):
            name = "decorated_strategy"
            description = "Decorated test"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        assert clean_registry.has_strategy("decorated_strategy")

    def test_unregister_component(self, clean_registry):
        """Test unregistering a component."""
        class TestStrategy(BaseStrategy):
            name = "temp_strategy"
            description = "Temporary"

            def validate_config(self, config):
                return True

            async def evaluate(self, input_data, context, providers):
                pass

        clean_registry.register(TestStrategy)
        assert clean_registry.has_strategy("temp_strategy")

        result = clean_registry.unregister("temp_strategy", ComponentType.STRATEGY)
        assert result is True
        assert clean_registry.has_strategy("temp_strategy") is False


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Tests for configuration system."""

    def test_strategy_config_defaults(self):
        """Test StrategyConfig default values."""
        config = StrategyConfig(name="test")
        assert config.enabled is True
        assert config.config == {}

    def test_analyzer_config_blocking_default(self):
        """Test AnalyzerConfig blocking default."""
        config = AnalyzerConfig(name="test")
        assert config.blocking is True

    def test_trustchain_config_from_dict(self):
        """Test creating TrustChainConfig from dictionary."""
        config_dict = {
            "decision_type": "test_type",
            "strategies": [
                {"name": "strategy1", "config": {"key": "value"}}
            ],
            "analyzers": [
                {"name": "analyzer1", "blocking": False}
            ],
            "outputs": [
                {"name": "output1"}
            ],
            "thresholds": {
                "min_confidence": 0.8,
                "auto_approve_threshold": 0.95
            }
        }

        config = TrustChainConfig.from_dict(config_dict)

        assert config.decision_type == "test_type"
        assert len(config.strategies) == 1
        assert config.strategies[0].name == "strategy1"
        assert config.strategies[0].config == {"key": "value"}
        assert len(config.analyzers) == 1
        assert config.analyzers[0].blocking is False
        assert config.min_confidence == 0.8

    def test_trustchain_config_simple_names(self):
        """Test config with just component names (no full objects)."""
        config_dict = {
            "decision_type": "simple",
            "strategies": ["strategy1", "strategy2"],
            "analyzers": ["analyzer1"],
            "outputs": ["output1"],
        }

        config = TrustChainConfig.from_dict(config_dict)

        assert len(config.strategies) == 2
        assert config.strategies[0].name == "strategy1"
        assert config.strategies[1].name == "strategy2"

    def test_trustchain_config_validation(self):
        """Test configuration validation."""
        config = TrustChainConfig(
            decision_type="test",
            min_confidence=1.5,  # Invalid
            auto_deny_threshold=0.9,
            auto_approve_threshold=0.1,  # Invalid (deny > approve)
            fail_open=True,  # Dangerous
        )

        errors = config.validate()

        assert any("min_confidence" in e for e in errors)
        assert any("auto_deny_threshold" in e for e in errors)
        assert any("WARNING" in e and "fail_open" in e for e in errors)

    def test_trustchain_config_to_dict(self):
        """Test configuration serialization."""
        config = TrustChainConfig(
            decision_type="test_type",
            strategies=[StrategyConfig(name="s1")],
            analyzers=[AnalyzerConfig(name="a1", blocking=False)],
            outputs=[OutputConfig(name="o1")],
            min_confidence=0.75,
        )

        config_dict = config.to_dict()

        assert config_dict["decision_type"] == "test_type"
        assert len(config_dict["strategies"]) == 1
        assert config_dict["thresholds"]["min_confidence"] == 0.75

    def test_get_enabled_components(self):
        """Test filtering enabled components."""
        config = TrustChainConfig(
            decision_type="test",
            strategies=[
                StrategyConfig(name="enabled", enabled=True),
                StrategyConfig(name="disabled", enabled=False),
            ],
            analyzers=[
                AnalyzerConfig(name="blocking", blocking=True),
                AnalyzerConfig(name="non_blocking", blocking=False),
            ],
        )

        enabled_strategies = config.get_enabled_strategies()
        assert len(enabled_strategies) == 1
        assert enabled_strategies[0].name == "enabled"

        blocking_analyzers = config.get_blocking_analyzers()
        assert len(blocking_analyzers) == 1
        assert blocking_analyzers[0].name == "blocking"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for core abstractions working together."""

    def test_full_result_flow(self, clean_registry):
        """Test creating and processing a full result."""
        # Create strategy result
        strategy_result = StrategyResult(
            strategy_name="consensus",
            decision=DecisionOutcome.APPROVED,
            confidence=0.88,
            reasoning="All models agree",
            agreement_level=1.0,
        )

        # Create analysis result
        analysis_result = AnalysisResult(
            analyzer_name="bias_check",
            passed=True,
            flags=[],
            warnings=[],
        )

        # Create accountability result
        result = AccountabilityResult(
            result_id="tc_integration_test",
            case_id="case_integration",
            decision_type="test",
            final_decision=DecisionOutcome.APPROVED,
            overall_confidence=0.88,
            requires_human_review=False,
            strategy_result=strategy_result,
            analysis_results=[analysis_result],
            primary_reasoning="All checks passed",
        )

        # Finalize
        input_data = {"applicant": "test", "amount": 1000}
        result.finalize(input_data)

        # Verify
        assert result.verify_integrity() is True
        assert result.audit_hash != ""
        assert result.input_data_hash != ""

        # Serialize
        result_dict = result.to_dict()
        assert result_dict["result_id"] == "tc_integration_test"
        assert result_dict["final_decision"] == "approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
