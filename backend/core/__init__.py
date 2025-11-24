"""
TrustChain Core Abstractions

This module provides the foundational abstractions for the TrustChain
accountability framework:

- Base classes for pluggable components (strategies, analyzers, outputs)
- Result objects for unified output
- Plugin registry for dynamic component discovery
- Configuration system for YAML-based setup

Built with care by Kareem & Claude
"""

from .base import (
    ComponentType,
    BaseComponent,
    BaseStrategy,
    BaseAnalyzer,
    BaseOutput,
)
from .result import (
    DecisionOutcome,
    ReviewTrigger,
    StrategyResult,
    AnalysisResult,
    AccountabilityResult,
)
from .registry import (
    ComponentRegistry,
    get_registry,
    register_component,
)
from .config import (
    StrategyConfig,
    AnalyzerConfig,
    OutputConfig,
    TrustChainConfig,
)

__all__ = [
    # Base classes
    "ComponentType",
    "BaseComponent",
    "BaseStrategy",
    "BaseAnalyzer",
    "BaseOutput",
    # Result objects
    "DecisionOutcome",
    "ReviewTrigger",
    "StrategyResult",
    "AnalysisResult",
    "AccountabilityResult",
    # Registry
    "ComponentRegistry",
    "get_registry",
    "register_component",
    # Config
    "StrategyConfig",
    "AnalyzerConfig",
    "OutputConfig",
    "TrustChainConfig",
]
