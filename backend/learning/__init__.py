"""
TrustChain Learning System

Takes human feedback and improves future decisions by:
1. Adjusting model weights in multi-model consensus
2. Calibrating confidence scores
3. Tuning analyzer sensitivity
4. Identifying patterns in overrides

Includes safeguards against bad actors:
- Reviewer credibility scoring (outcome-based, not opinion-based)
- Anomaly detection for unusual override patterns
- Outcome-gated learning (reality > opinions)
- Single reviewer influence caps
- Versioned parameters with rollback

Usage:
    from learning import LearningEngine, LearnedParameters, LearningGuard
    from feedback import get_feedback_store

    store = get_feedback_store()
    guard = LearningGuard()
    engine = LearningEngine(store, safeguard=guard)

    # Learn from accumulated feedback (with safeguards)
    results = await engine.learn()

    # Get learned parameters
    params = engine.get_parameters("hiring")

    # Apply to TrustChain
    tc = TrustChain.from_config("configs/hiring.yaml", learned_parameters=params)

Built with care by Kareem & Claude
"""

from .engine import (
    ModelWeight,
    ConfidenceCalibration,
    AnalyzerTuning,
    LearnedParameters,
    LearningEngine,
)

from .safeguards import (
    AnomalyType,
    ReviewerCredibility,
    LearningGuard,
    ParameterVersion,
)

__all__ = [
    # Engine
    "ModelWeight",
    "ConfidenceCalibration",
    "AnalyzerTuning",
    "LearnedParameters",
    "LearningEngine",
    # Safeguards
    "AnomalyType",
    "ReviewerCredibility",
    "LearningGuard",
    "ParameterVersion",
]
