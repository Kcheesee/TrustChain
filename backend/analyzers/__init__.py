"""
TrustChain Analysis Modules

Analyzers examine evaluation results for specific issues:

- protected_attributes: Direct mentions of protected characteristics
- proxy_variables: Indirect indicators of protected characteristics (Phase 2)
- confidence_calibration: Is confidence score well-calibrated? (Phase 2)
- reasoning_quality: Is the reasoning sound and complete? (Phase 2)
- gap_analysis: Are all criteria addressed? (Phase 2)
- outcome_patterns: Historical bias patterns (Phase 2)

Usage:
    from analyzers import ProtectedAttributesAnalyzer

    analyzer = ProtectedAttributesAnalyzer(config={
        "sensitivity": "high"
    })
    result = analyzer.analyze(strategy_result, input_data, context)

Built with care by Kareem & Claude
"""

from core.base import BaseAnalyzer
from core.registry import register_component

# Import analyzers here as they're implemented
from .protected_attributes import ProtectedAttributesAnalyzer
from .proxy_variables import ProxyVariablesAnalyzer
from .counterfactual_generator import (
    CounterfactualGenerator,
    Counterfactual,
    CounterfactualModification,
    ProtectedAttribute,
)
from .counterfactual_fairness import (
    CounterfactualFairnessAnalyzer,
    CounterfactualResult,
    CounterfactualFairnessResult,
    BiasStrength,
)

__all__ = [
    "BaseAnalyzer",
    "ProtectedAttributesAnalyzer",
    "ProxyVariablesAnalyzer",
    # Counterfactual Fairness (Phase 5)
    "CounterfactualGenerator",
    "Counterfactual",
    "CounterfactualModification",
    "ProtectedAttribute",
    "CounterfactualFairnessAnalyzer",
    "CounterfactualResult",
    "CounterfactualFairnessResult",
    "BiasStrength",
]
