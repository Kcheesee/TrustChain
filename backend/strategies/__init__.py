"""
TrustChain Evaluation Strategies

Strategies determine HOW accountability is established for AI decisions.
Each strategy implements a different approach:

- multi_model_consensus: Multiple models vote on decisions
- criteria_decomposition: Break decision into scored criteria (Phase 2)
- adversarial_review: Challenge decisions with counter-arguments (Phase 2)
- multi_pass: Same model evaluates multiple times (Phase 2)
- constitutional_check: Verify against predefined principles (Phase 2)
- historical_consistency: Compare with past similar decisions (Phase 2)

Usage:
    from strategies import MultiModelConsensusStrategy

    strategy = MultiModelConsensusStrategy(config={
        "consensus_threshold": 0.66,
        "require_unanimous": False
    })
    result = await strategy.evaluate(input_data, context, providers)

Built with care by Kareem & Claude
"""

from core.base import BaseStrategy
from core.registry import register_component

# Import strategies here as they're implemented
from .multi_model_consensus import MultiModelConsensusStrategy
from .criteria_decomposition import CriteriaDecompositionStrategy
from .adversarial_review import AdversarialReviewStrategy

__all__ = [
    "BaseStrategy",
    "MultiModelConsensusStrategy",
    "CriteriaDecompositionStrategy",
    "AdversarialReviewStrategy",
]
