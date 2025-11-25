"""
TrustChain Feedback System

Captures and stores human feedback on AI decisions to enable
continuous learning and improvement.

Components:
- capture: HumanFeedback dataclass, ReviewerAction enum
- storage: FeedbackStore implementations (SQLite, In-Memory)

Usage:
    from feedback import HumanFeedback, ReviewerAction, get_feedback_store

    feedback = HumanFeedback(
        result_id="tc_123",
        case_id="case_456",
        reviewer_id="jane_hr",
        action=ReviewerAction.AGREE_APPROVE,
        reasoning="Decision looks correct"
    )

    store = get_feedback_store()
    await store.save_feedback(feedback)

Built with care by Kareem & Claude
"""

from .capture import (
    ReviewerAction,
    OverrideReason,
    HumanFeedback,
    FeedbackStats,
)
from .storage import (
    FeedbackStore,
    InMemoryFeedbackStore,
    SQLiteFeedbackStore,
    get_feedback_store,
)

__all__ = [
    "ReviewerAction",
    "OverrideReason",
    "HumanFeedback",
    "FeedbackStats",
    "FeedbackStore",
    "InMemoryFeedbackStore",
    "SQLiteFeedbackStore",
    "get_feedback_store",
]
