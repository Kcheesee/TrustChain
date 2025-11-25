"""
Feedback Capture Module for TrustChain.

Defines data structures for capturing human feedback on AI decisions.
This feedback enables the learning engine to improve over time.

Key Classes:
- ReviewerAction: What the human decided (agree, override, escalate)
- OverrideReason: Why they overrode TrustChain
- HumanFeedback: Complete feedback record
- FeedbackStats: Aggregated statistics

Built with care by Kareem & Claude
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import hashlib
import json


class ReviewerAction(str, Enum):
    """What the human reviewer decided."""

    # Agreement actions
    AGREE_APPROVE = "agree_approve"      # TC said approve, human agrees
    AGREE_DENY = "agree_deny"            # TC said deny, human agrees
    AGREE_FLAG = "agree_flag"            # TC flagged for review, human agrees it needed review

    # Override actions
    OVERRIDE_TO_APPROVE = "override_approve"  # TC said deny/flag, human approves anyway
    OVERRIDE_TO_DENY = "override_deny"        # TC said approve/flag, human denies

    # Other actions
    ESCALATE = "escalate"                # Human escalates to higher authority
    REQUEST_MORE_INFO = "request_info"   # Can't decide, need more data
    DEFER = "defer"                      # Postpone decision

    @property
    def is_agreement(self) -> bool:
        """Check if this action agrees with TrustChain."""
        return self in [
            ReviewerAction.AGREE_APPROVE,
            ReviewerAction.AGREE_DENY,
            ReviewerAction.AGREE_FLAG,
        ]

    @property
    def is_override(self) -> bool:
        """Check if this action overrides TrustChain."""
        return self in [
            ReviewerAction.OVERRIDE_TO_APPROVE,
            ReviewerAction.OVERRIDE_TO_DENY,
        ]


class OverrideReason(str, Enum):
    """Why the human overrode TrustChain's decision."""

    # Context issues
    CONTEXT_NOT_CAPTURED = "context_not_captured"  # TC missed relevant context
    ADDITIONAL_INFO = "additional_info"            # Human had info TC didn't see

    # False positive/negative
    FALSE_POSITIVE_BIAS = "false_positive_bias"    # Flag was wrong - no actual bias
    FALSE_NEGATIVE_BIAS = "false_negative_bias"    # Should have flagged, didn't

    # Policy/rule issues
    POLICY_EXCEPTION = "policy_exception"          # Special case allowed by policy
    CRITERIA_MISAPPLIED = "criteria_misapplied"    # AI got the rules wrong
    OUTDATED_POLICY = "outdated_policy"            # Policy has changed

    # Model issues
    MODEL_HALLUCINATION = "model_hallucination"    # AI made stuff up
    MODEL_MISUNDERSTANDING = "model_misunderstanding"  # AI didn't understand context
    CONFIDENCE_MISCALIBRATED = "confidence_miscalibrated"  # AI was over/under confident

    # Edge cases
    EDGE_CASE = "edge_case"                        # Unusual situation not covered
    COMPETING_PRIORITIES = "competing_priorities"  # Multiple valid interpretations

    # Other
    OTHER = "other"


@dataclass
class HumanFeedback:
    """
    Captured feedback from human reviewer.

    This is the core data structure that feeds the learning engine.
    Every field matters for understanding what went right/wrong.
    """

    # === Link to original decision ===
    result_id: str  # TrustChain result ID
    case_id: str    # Original case ID

    # === Reviewer info ===
    reviewer_id: str
    reviewer_role: str = "reviewer"  # "sr_reviewer", "manager", "legal", etc.

    # === What they decided ===
    action: ReviewerAction = ReviewerAction.AGREE_FLAG
    override_reason: Optional[OverrideReason] = None

    # === Their reasoning (critical for learning) ===
    reasoning: str = ""

    # === What they saw that TC missed (or flagged incorrectly) ===
    additional_context: str = ""

    # === Specific analyzer feedback ===
    # Which analyzers incorrectly flagged?
    incorrect_flags: List[str] = field(default_factory=list)  # ["proxy_variables"]
    # Which analyzers should have flagged but didn't?
    missed_flags: List[str] = field(default_factory=list)     # ["protected_attributes"]

    # === Confidence in their decision ===
    reviewer_confidence: float = 1.0  # 0.0-1.0

    # === Metadata ===
    timestamp: datetime = field(default_factory=datetime.now)
    time_spent_seconds: Optional[int] = None  # How long they reviewed

    # === For outcome tracking (filled in later) ===
    outcome_tracked: bool = False
    final_outcome: Optional[str] = None  # What actually happened months later
    outcome_timestamp: Optional[datetime] = None
    outcome_notes: str = ""

    # === Generated fields ===
    feedback_id: str = ""  # Generated on save

    def __post_init__(self):
        """Validate and generate feedback ID."""
        if not self.feedback_id:
            self.feedback_id = self._generate_id()

        # Validate override reason is provided for override actions
        if self.action.is_override and not self.override_reason:
            # Default to OTHER if not specified
            self.override_reason = OverrideReason.OTHER

    def _generate_id(self) -> str:
        """Generate unique feedback ID."""
        content = f"{self.result_id}:{self.reviewer_id}:{self.timestamp.isoformat()}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"fb_{hash_val}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "feedback_id": self.feedback_id,
            "result_id": self.result_id,
            "case_id": self.case_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "action": self.action.value,
            "override_reason": self.override_reason.value if self.override_reason else None,
            "reasoning": self.reasoning,
            "additional_context": self.additional_context,
            "incorrect_flags": self.incorrect_flags,
            "missed_flags": self.missed_flags,
            "reviewer_confidence": self.reviewer_confidence,
            "timestamp": self.timestamp.isoformat(),
            "time_spent_seconds": self.time_spent_seconds,
            "outcome_tracked": self.outcome_tracked,
            "final_outcome": self.final_outcome,
            "outcome_timestamp": self.outcome_timestamp.isoformat() if self.outcome_timestamp else None,
            "outcome_notes": self.outcome_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanFeedback":
        """Create from dictionary."""
        return cls(
            feedback_id=data.get("feedback_id", ""),
            result_id=data["result_id"],
            case_id=data["case_id"],
            reviewer_id=data["reviewer_id"],
            reviewer_role=data.get("reviewer_role", "reviewer"),
            action=ReviewerAction(data["action"]),
            override_reason=OverrideReason(data["override_reason"]) if data.get("override_reason") else None,
            reasoning=data.get("reasoning", ""),
            additional_context=data.get("additional_context", ""),
            incorrect_flags=data.get("incorrect_flags", []),
            missed_flags=data.get("missed_flags", []),
            reviewer_confidence=data.get("reviewer_confidence", 1.0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.now()),
            time_spent_seconds=data.get("time_spent_seconds"),
            outcome_tracked=data.get("outcome_tracked", False),
            final_outcome=data.get("final_outcome"),
            outcome_timestamp=datetime.fromisoformat(data["outcome_timestamp"]) if data.get("outcome_timestamp") else None,
            outcome_notes=data.get("outcome_notes", ""),
        )


@dataclass
class FeedbackStats:
    """Aggregated statistics from feedback."""

    # === Volume ===
    total_decisions: int = 0
    total_reviewed: int = 0
    total_overrides: int = 0

    # === Time period ===
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # === Agreement rates ===
    agreement_rate: float = 0.0   # How often humans agree with TC
    override_rate: float = 0.0    # How often humans override TC

    # === Accuracy by analyzer ===
    analyzer_accuracy: Dict[str, float] = field(default_factory=dict)
    # e.g., {"proxy_variables": 0.89, "protected_attributes": 0.95}

    analyzer_false_positives: Dict[str, int] = field(default_factory=dict)
    analyzer_false_negatives: Dict[str, int] = field(default_factory=dict)

    # === Accuracy by model (for multi-model consensus) ===
    model_accuracy: Dict[str, float] = field(default_factory=dict)
    # e.g., {"anthropic": 0.91, "openai": 0.87, "llama": 0.82}

    # === False positive/negative rates ===
    false_positive_rate: float = 0.0  # Flagged but shouldn't have
    false_negative_rate: float = 0.0  # Didn't flag but should have

    # === By decision type ===
    accuracy_by_type: Dict[str, float] = field(default_factory=dict)
    # e.g., {"hiring": 0.88, "lending": 0.92}

    volume_by_type: Dict[str, int] = field(default_factory=dict)

    # === Override reasons breakdown ===
    override_reasons: Dict[str, int] = field(default_factory=dict)
    # e.g., {"false_positive_bias": 12, "context_not_captured": 8}

    # === Reviewer metrics ===
    avg_review_time_seconds: Optional[float] = None
    reviewer_agreement_rates: Dict[str, float] = field(default_factory=dict)

    # === Outcome tracking ===
    outcomes_tracked: int = 0
    outcome_accuracy: float = 0.0  # When we track outcomes, was decision good?

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "volume": {
                "total_decisions": self.total_decisions,
                "total_reviewed": self.total_reviewed,
                "total_overrides": self.total_overrides,
            },
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "rates": {
                "agreement_rate": self.agreement_rate,
                "override_rate": self.override_rate,
                "false_positive_rate": self.false_positive_rate,
                "false_negative_rate": self.false_negative_rate,
            },
            "by_analyzer": {
                "accuracy": self.analyzer_accuracy,
                "false_positives": self.analyzer_false_positives,
                "false_negatives": self.analyzer_false_negatives,
            },
            "by_model": self.model_accuracy,
            "by_decision_type": {
                "accuracy": self.accuracy_by_type,
                "volume": self.volume_by_type,
            },
            "override_reasons": self.override_reasons,
            "reviewer_metrics": {
                "avg_review_time_seconds": self.avg_review_time_seconds,
                "agreement_by_reviewer": self.reviewer_agreement_rates,
            },
            "outcomes": {
                "tracked": self.outcomes_tracked,
                "accuracy": self.outcome_accuracy,
            },
        }
