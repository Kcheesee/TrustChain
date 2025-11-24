"""
TrustChain Core Base Classes

Abstract base classes for all pluggable TrustChain components:
- BaseComponent: Foundation for all plugins
- BaseStrategy: Evaluation strategies (how accountability is established)
- BaseAnalyzer: Analysis modules (what to check for)
- BaseOutput: Output generators (formatting for different audiences)

Built with care by Kareem & Claude
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .result import StrategyResult, AnalysisResult, AccountabilityResult


class ComponentType(str, Enum):
    """Types of pluggable components in TrustChain."""
    STRATEGY = "strategy"
    ANALYZER = "analyzer"
    OUTPUT = "output"


class BaseComponent(ABC):
    """
    Base class for all pluggable TrustChain components.

    All strategies, analyzers, and outputs inherit from this class.
    Provides common metadata and configuration validation.

    Attributes:
        component_type: The type of component (strategy, analyzer, output)
        name: Unique identifier for this component
        description: Human-readable description of what this component does
        version: Semantic version string
    """

    component_type: ComponentType
    name: str
    description: str
    version: str = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the component with optional configuration.

        Args:
            config: Component-specific configuration dictionary
        """
        self.config = config or {}
        if self.config:
            self.validate_config(self.config)

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate component configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Return component metadata for registry and introspection.

        Returns:
            Dictionary containing component metadata
        """
        return {
            "name": self.name,
            "type": self.component_type.value,
            "description": self.description,
            "version": self.version,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, version={self.version})>"


class BaseStrategy(BaseComponent):
    """
    Base class for evaluation strategies.

    Strategies determine HOW accountability is established for AI decisions.
    Different strategies work with different model configurations:

    - Multi-model consensus: Multiple models vote on decisions
    - Criteria decomposition: Break decision into scored criteria
    - Adversarial review: Challenge decisions with counter-arguments
    - Multi-pass: Same model evaluates multiple times
    - Constitutional check: Verify against predefined principles
    - Historical consistency: Compare with past similar decisions

    Subclasses must implement:
        - evaluate(): Execute the evaluation strategy
        - validate_config(): Validate strategy-specific configuration

    Example:
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            description = "Custom evaluation strategy"

            async def evaluate(self, input_data, context, providers):
                # Implementation here
                return StrategyResult(...)

            def validate_config(self, config):
                return True
    """

    component_type = ComponentType.STRATEGY

    # Whether this strategy requires multiple LLM providers
    requires_multiple_providers: bool = False

    # Minimum number of providers needed (if requires_multiple_providers)
    min_providers: int = 1

    @abstractmethod
    async def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        providers: List[Any]
    ) -> "StrategyResult":
        """
        Execute the evaluation strategy.

        This is the core method that each strategy must implement.
        It takes input data, policy context, and available LLM providers,
        then returns a structured result.

        Args:
            input_data: The case/application data to evaluate
                       (e.g., benefit application, resume, loan request)
            context: Policy context, evaluation criteria, principles, etc.
                    (e.g., eligibility rules, job requirements)
            providers: Available LLM providers (may be one or many)
                      Each provider is a BaseLLMProvider instance

        Returns:
            StrategyResult with decision, reasoning, confidence, and metadata

        Raises:
            ValueError: If input data or context is invalid
            ProviderException: If all providers fail
        """
        pass

    def can_execute(self, providers: List[Any]) -> bool:
        """
        Check if this strategy can execute with the given providers.

        Args:
            providers: List of available LLM providers

        Returns:
            True if strategy can execute, False otherwise
        """
        if self.requires_multiple_providers:
            return len(providers) >= self.min_providers
        return len(providers) >= 1


class BaseAnalyzer(BaseComponent):
    """
    Base class for analysis modules.

    Analyzers examine evaluation results for specific issues:

    - Protected attributes: Direct mentions of protected characteristics
    - Proxy variables: Indirect indicators of protected characteristics
    - Confidence calibration: Is confidence score well-calibrated?
    - Reasoning quality: Is the reasoning sound and complete?
    - Gap analysis: Are all criteria addressed?
    - Outcome patterns: Historical bias patterns

    Analyzers can be:
    - Blocking: Failures require human review
    - Non-blocking: Issues are flagged but don't halt processing

    Subclasses must implement:
        - analyze(): Examine the strategy result
        - validate_config(): Validate analyzer-specific configuration

    Example:
        class MyAnalyzer(BaseAnalyzer):
            name = "my_analyzer"
            description = "Custom analysis module"

            def analyze(self, strategy_result, input_data, context):
                # Implementation here
                return AnalysisResult(...)

            def validate_config(self, config):
                return True
    """

    component_type = ComponentType.ANALYZER

    # If True, analysis failures require human review
    blocking: bool = True

    @abstractmethod
    def analyze(
        self,
        strategy_result: "StrategyResult",
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> "AnalysisResult":
        """
        Analyze the strategy result for issues.

        Examines the evaluation output and original input for problems
        like bias, logical errors, missing information, etc.

        Args:
            strategy_result: Output from the evaluation strategy
            input_data: Original case/application data
            context: Policy context and criteria

        Returns:
            AnalysisResult with findings, flags, warnings, and recommendations
        """
        pass

    async def analyze_async(
        self,
        strategy_result: "StrategyResult",
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> "AnalysisResult":
        """
        Async version of analyze for analyzers that need LLM calls.

        Default implementation calls the sync analyze method.
        Override this for analyzers that need async operations.

        Args:
            strategy_result: Output from the evaluation strategy
            input_data: Original case/application data
            context: Policy context and criteria

        Returns:
            AnalysisResult with findings, flags, warnings, and recommendations
        """
        return self.analyze(strategy_result, input_data, context)


class BaseOutput(BaseComponent):
    """
    Base class for output generators.

    Outputs format accountability results for specific audiences:

    - Internal audit: Detailed logs for compliance teams
    - Consumer explanation: Plain-language summaries for applicants
    - Compliance report: Formatted reports for regulators
    - Training signal: Feedback for model improvement
    - Appeal package: Documentation for appeals process

    Different outputs may include different levels of detail
    and use different formats (JSON, PDF, plain text, etc.).

    Subclasses must implement:
        - generate(): Create the formatted output
        - validate_config(): Validate output-specific configuration

    Example:
        class MyOutput(BaseOutput):
            name = "my_output"
            description = "Custom output generator"

            def generate(self, accountability_result):
                # Implementation here
                return {"formatted": "output"}

            def validate_config(self, config):
                return True
    """

    component_type = ComponentType.OUTPUT

    # Output format identifier (json, text, pdf, etc.)
    output_format: str = "json"

    @abstractmethod
    def generate(
        self,
        accountability_result: "AccountabilityResult"
    ) -> Any:
        """
        Generate formatted output from the accountability result.

        Takes the complete TrustChain result and formats it
        appropriately for the target audience.

        Args:
            accountability_result: Complete result from TrustChain evaluation

        Returns:
            Formatted output (dict, string, bytes, etc. depending on format)
        """
        pass

    async def generate_async(
        self,
        accountability_result: "AccountabilityResult"
    ) -> Any:
        """
        Async version of generate for outputs that need external calls.

        Default implementation calls the sync generate method.
        Override this for outputs that need async operations
        (e.g., generating PDFs via external service).

        Args:
            accountability_result: Complete result from TrustChain evaluation

        Returns:
            Formatted output
        """
        return self.generate(accountability_result)
