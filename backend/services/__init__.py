"""
TrustChain Services Module

Exports business logic services.

The TrustChain service is the new primary entry point for the
modular accountability framework. The DecisionOrchestrator is
kept for backward compatibility.

Built with care by Kareem & Claude
"""

from .orchestrator import DecisionOrchestrator
from .bias_detection import BiasDetectionService, get_bias_detector
from .trustchain import TrustChain

__all__ = [
    # New modular service
    "TrustChain",
    # Legacy services (kept for backward compatibility)
    "DecisionOrchestrator",
    "BiasDetectionService",
    "get_bias_detector",
]
