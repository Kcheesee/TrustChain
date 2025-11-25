"""
Learning Safeguards for TrustChain.

Protects the learning system against bad actors who might:
- Deliberately override AI decisions to inject bias
- Game the system through consistent false feedback
- Dominate the training signal with one perspective

Key Protections:
1. Reviewer Credibility Scoring - Track against outcomes, not just opinions
2. Anomaly Detection - Flag unusual override patterns
3. Outcome-Gated Learning - Don't trust feedback until verified by reality
4. Single Reviewer Cap - No one person dominates the learning
5. Versioned Parameters + Rollback - Detect and revert corruption

CRITICAL: Reviewer opinion is NOT ground truth. Reality (outcomes) is.

Built with care by Kareem & Claude
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import hashlib
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of detected anomalies in reviewer behavior."""
    HIGH_OVERRIDE_RATE = "high_override_rate"
    POOR_OUTCOME_ACCURACY = "poor_outcome_accuracy"
    CONCENTRATION_BIAS = "concentration_bias"  # Overrides certain flags disproportionately
    SPEED_ANOMALY = "speed_anomaly"  # Reviews too fast
    PATTERN_DEVIATION = "pattern_deviation"  # Suddenly changed behavior
    SINGLE_REVIEWER_DOMINANCE = "single_reviewer_dominance"


@dataclass
class ReviewerCredibility:
    """
    Track reviewer credibility based on outcome accuracy.

    Ground truth = what actually happens months later.
    NOT whether they agreed with AI or other reviewers.
    """

    reviewer_id: str

    # === Outcome-Based Accuracy ===
    total_decisions_with_outcomes: int = 0
    correct_outcomes: int = 0  # Their decision led to good outcome

    # === Override Patterns ===
    total_reviews: int = 0
    total_overrides: int = 0
    override_by_type: Dict[str, int] = field(default_factory=dict)  # "proxy_variables": 15

    # === Derived Scores ===
    @property
    def outcome_accuracy(self) -> float:
        """Accuracy based on tracked outcomes (ground truth)."""
        if self.total_decisions_with_outcomes == 0:
            return 0.5  # No data, neutral
        return self.correct_outcomes / self.total_decisions_with_outcomes

    @property
    def override_rate(self) -> float:
        """How often this reviewer overrides AI."""
        if self.total_reviews == 0:
            return 0.0
        return self.total_overrides / self.total_reviews

    @property
    def credibility_score(self) -> float:
        """
        Overall credibility score [0-1].

        Based primarily on outcome accuracy, with penalty for
        extreme override behavior.
        """
        if self.total_decisions_with_outcomes < 5:
            # Insufficient outcome data - give benefit of doubt but cap at 0.7
            return min(0.7, 0.5 + (0.2 * (1 - abs(self.override_rate - 0.15))))

        # Primary: outcome accuracy
        base_score = self.outcome_accuracy

        # Penalty for extreme override rates (either way)
        # Typical override rate is 10-20%. Penalize if way outside that.
        override_penalty = 0.0
        if self.override_rate > 0.4:  # >40% override rate
            override_penalty = (self.override_rate - 0.4) * 0.3
        elif self.override_rate < 0.05 and self.total_reviews > 20:  # <5% with many reviews
            # Too agreeable could indicate rubber-stamping
            override_penalty = 0.1

        return max(0.1, base_score - override_penalty)

    # === Time tracking ===
    first_review: Optional[datetime] = None
    last_review: Optional[datetime] = None
    avg_review_time_seconds: Optional[float] = None

    # === Alerts ===
    anomalies_detected: List[AnomalyType] = field(default_factory=list)
    flagged_for_review: bool = False
    flag_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "reviewer_id": self.reviewer_id,
            "total_reviews": self.total_reviews,
            "total_overrides": self.total_overrides,
            "override_rate": self.override_rate,
            "total_decisions_with_outcomes": self.total_decisions_with_outcomes,
            "correct_outcomes": self.correct_outcomes,
            "outcome_accuracy": self.outcome_accuracy,
            "credibility_score": self.credibility_score,
            "override_by_type": self.override_by_type,
            "anomalies_detected": [a.value for a in self.anomalies_detected],
            "flagged_for_review": self.flagged_for_review,
            "flag_reason": self.flag_reason,
            "first_review": self.first_review.isoformat() if self.first_review else None,
            "last_review": self.last_review.isoformat() if self.last_review else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewerCredibility":
        """Create from dictionary."""
        return cls(
            reviewer_id=data["reviewer_id"],
            total_reviews=data.get("total_reviews", 0),
            total_overrides=data.get("total_overrides", 0),
            total_decisions_with_outcomes=data.get("total_decisions_with_outcomes", 0),
            correct_outcomes=data.get("correct_outcomes", 0),
            override_by_type=data.get("override_by_type", {}),
            anomalies_detected=[AnomalyType(a) for a in data.get("anomalies_detected", [])],
            flagged_for_review=data.get("flagged_for_review", False),
            flag_reason=data.get("flag_reason", ""),
            first_review=datetime.fromisoformat(data["first_review"]) if data.get("first_review") else None,
            last_review=datetime.fromisoformat(data["last_review"]) if data.get("last_review") else None,
            avg_review_time_seconds=data.get("avg_review_time_seconds"),
        )


@dataclass
class OutcomeGatedFeedback:
    """
    Feedback that's waiting for outcome verification.

    We don't learn from this until we know the actual outcome.
    """

    feedback_id: str
    result_id: str
    reviewer_id: str
    reviewer_decision: str  # "approve" / "deny"
    was_override: bool
    submitted_at: datetime

    # Filled in later
    outcome: Optional[str] = None
    outcome_at: Optional[datetime] = None
    verified: bool = False

    # Was the reviewer right?
    reviewer_correct: Optional[bool] = None


@dataclass
class ParameterVersion:
    """
    Versioned snapshot of learned parameters for rollback.

    If corruption is detected, we can revert to last known good state.
    """

    version: int
    timestamp: datetime
    parameters_hash: str  # SHA-256 of parameter state
    parameters_snapshot: Dict[str, Any]

    # Validation metrics at time of save
    avg_reviewer_credibility: float
    outcome_sample_size: int

    # Was this version validated?
    validated: bool = False
    validation_notes: str = ""


class LearningGuard:
    """
    Safeguards for the TrustChain learning system.

    Key principles:
    1. Reality (outcomes) beats opinions (feedback)
    2. No single reviewer dominates
    3. Unusual patterns get flagged
    4. We can always roll back
    """

    def __init__(
        self,
        max_reviewer_influence: float = 0.15,  # No reviewer > 15% of training signal
        outcome_wait_days: int = 90,  # Wait 90 days for outcome before learning
        min_outcome_sample: int = 20,  # Need 20+ outcomes before trusting learning
        anomaly_override_threshold: float = 0.4,  # Flag if >40% override rate
        min_credibility_for_learning: float = 0.3,  # Ignore reviewers below 0.3
        state_path: Optional[str] = None
    ):
        self.max_reviewer_influence = max_reviewer_influence
        self.outcome_wait_days = outcome_wait_days
        self.min_outcome_sample = min_outcome_sample
        self.anomaly_override_threshold = anomaly_override_threshold
        self.min_credibility = min_credibility_for_learning
        self.state_path = state_path

        # State
        self.reviewer_credibility: Dict[str, ReviewerCredibility] = {}
        self.pending_outcomes: List[OutcomeGatedFeedback] = []
        self.parameter_versions: List[ParameterVersion] = []
        self.current_version: int = 0

        # Anomaly tracking
        self.detected_anomalies: List[Dict[str, Any]] = []

        if state_path:
            self._load_state()

        logger.info(
            f"LearningGuard initialized: "
            f"max_influence={max_reviewer_influence:.0%}, "
            f"outcome_wait={outcome_wait_days}d, "
            f"min_sample={min_outcome_sample}"
        )

    def record_review(
        self,
        reviewer_id: str,
        was_override: bool,
        override_flag_type: Optional[str] = None,
        review_time_seconds: Optional[int] = None
    ):
        """
        Record a review for credibility tracking.

        Call this when a reviewer submits feedback.
        """
        if reviewer_id not in self.reviewer_credibility:
            self.reviewer_credibility[reviewer_id] = ReviewerCredibility(reviewer_id=reviewer_id)

        cred = self.reviewer_credibility[reviewer_id]
        cred.total_reviews += 1

        if was_override:
            cred.total_overrides += 1
            if override_flag_type:
                cred.override_by_type[override_flag_type] = (
                    cred.override_by_type.get(override_flag_type, 0) + 1
                )

        # Update timestamps
        now = datetime.now()
        if cred.first_review is None:
            cred.first_review = now
        cred.last_review = now

        # Update average review time
        if review_time_seconds:
            if cred.avg_review_time_seconds is None:
                cred.avg_review_time_seconds = float(review_time_seconds)
            else:
                # Running average
                n = cred.total_reviews
                cred.avg_review_time_seconds = (
                    cred.avg_review_time_seconds * (n - 1) + review_time_seconds
                ) / n

        # Check for anomalies after each review
        self._check_reviewer_anomalies(cred)

    def record_outcome(
        self,
        feedback_id: str,
        result_id: str,
        reviewer_id: str,
        outcome: str,
        reviewer_decision_correct: bool
    ):
        """
        Record the actual outcome of a decision.

        This is the GROUND TRUTH that updates reviewer credibility.
        """
        if reviewer_id not in self.reviewer_credibility:
            self.reviewer_credibility[reviewer_id] = ReviewerCredibility(reviewer_id=reviewer_id)

        cred = self.reviewer_credibility[reviewer_id]
        cred.total_decisions_with_outcomes += 1

        if reviewer_decision_correct:
            cred.correct_outcomes += 1

        logger.info(
            f"Outcome recorded for {reviewer_id}: "
            f"correct={reviewer_decision_correct}, "
            f"new_accuracy={cred.outcome_accuracy:.0%}"
        )

    def get_reviewer_weight(self, reviewer_id: str) -> float:
        """
        Get the weight to apply to this reviewer's feedback.

        Low credibility = low weight. Flagged reviewers = zero weight.
        """
        if reviewer_id not in self.reviewer_credibility:
            # New reviewer - give partial weight until we have data
            return 0.5

        cred = self.reviewer_credibility[reviewer_id]

        if cred.flagged_for_review:
            logger.warning(f"Reviewer {reviewer_id} is flagged - zero weight")
            return 0.0

        if cred.credibility_score < self.min_credibility:
            logger.warning(
                f"Reviewer {reviewer_id} below credibility threshold "
                f"({cred.credibility_score:.2f} < {self.min_credibility:.2f})"
            )
            return 0.0

        return cred.credibility_score

    def apply_reviewer_caps(
        self,
        feedback_weights: Dict[str, float],
        total_feedback_count: int
    ) -> Dict[str, float]:
        """
        Cap reviewer influence to prevent single-reviewer dominance.

        Args:
            feedback_weights: Dict of reviewer_id -> total weight contribution
            total_feedback_count: Total feedback items

        Returns:
            Adjusted weights with caps applied
        """
        if not feedback_weights or total_feedback_count == 0:
            return feedback_weights

        max_contribution = total_feedback_count * self.max_reviewer_influence
        adjusted = {}

        for reviewer_id, weight in feedback_weights.items():
            if weight > max_contribution:
                old_weight = weight
                adjusted[reviewer_id] = max_contribution
                logger.warning(
                    f"Capped {reviewer_id} influence: {old_weight:.1f} -> {max_contribution:.1f} "
                    f"(max {self.max_reviewer_influence:.0%})"
                )

                # Flag for review if repeatedly hitting cap
                self._maybe_flag_dominance(reviewer_id)
            else:
                adjusted[reviewer_id] = weight

        return adjusted

    def should_learn_from_feedback(self, feedback_id: str, has_outcome: bool) -> Tuple[bool, str]:
        """
        Determine if we should learn from this feedback.

        Implements outcome-gated learning - we prefer feedback
        with verified outcomes over raw reviewer opinions.
        """
        if has_outcome:
            return True, "Has verified outcome"

        # Check if we have enough outcome-verified data
        total_with_outcomes = sum(
            c.total_decisions_with_outcomes for c in self.reviewer_credibility.values()
        )

        if total_with_outcomes < self.min_outcome_sample:
            # Not enough outcome data yet - allow learning but with warning
            return True, f"Insufficient outcomes ({total_with_outcomes}/{self.min_outcome_sample}), learning with caution"

        # We have enough outcome data - prefer to wait for outcomes
        return False, "Waiting for outcome verification"

    def _check_reviewer_anomalies(self, cred: ReviewerCredibility):
        """Check for anomalous behavior patterns."""
        anomalies = []

        # High override rate
        if cred.total_reviews >= 10 and cred.override_rate > self.anomaly_override_threshold:
            anomalies.append(AnomalyType.HIGH_OVERRIDE_RATE)

        # Poor outcome accuracy (if we have data)
        if cred.total_decisions_with_outcomes >= 10 and cred.outcome_accuracy < 0.5:
            anomalies.append(AnomalyType.POOR_OUTCOME_ACCURACY)

        # Concentration bias - overrides one type disproportionately
        if cred.total_overrides >= 10:
            for flag_type, count in cred.override_by_type.items():
                if count / cred.total_overrides > 0.7:  # >70% of overrides are one type
                    anomalies.append(AnomalyType.CONCENTRATION_BIAS)
                    break

        # Speed anomaly - reviewing too fast
        if cred.avg_review_time_seconds is not None and cred.avg_review_time_seconds < 10:
            anomalies.append(AnomalyType.SPEED_ANOMALY)

        if anomalies:
            cred.anomalies_detected = anomalies

            # Flag if multiple anomalies or severe single anomaly
            if (len(anomalies) >= 2 or
                AnomalyType.POOR_OUTCOME_ACCURACY in anomalies):
                cred.flagged_for_review = True
                cred.flag_reason = f"Anomalies detected: {[a.value for a in anomalies]}"

                self.detected_anomalies.append({
                    "reviewer_id": cred.reviewer_id,
                    "anomalies": [a.value for a in anomalies],
                    "timestamp": datetime.now().isoformat(),
                    "credibility": cred.credibility_score,
                })

                logger.warning(
                    f"🚨 Reviewer {cred.reviewer_id} flagged: {cred.flag_reason}"
                )

    def _maybe_flag_dominance(self, reviewer_id: str):
        """Check if a reviewer is dominating the training signal."""
        if reviewer_id not in self.reviewer_credibility:
            return

        cred = self.reviewer_credibility[reviewer_id]

        # If this reviewer has been capped 3+ times, flag for review
        # (Implementation: track in separate counter if needed)
        total_reviews_all = sum(c.total_reviews for c in self.reviewer_credibility.values())
        if cred.total_reviews / max(1, total_reviews_all) > 0.3:  # >30% of all reviews
            if AnomalyType.SINGLE_REVIEWER_DOMINANCE not in cred.anomalies_detected:
                cred.anomalies_detected.append(AnomalyType.SINGLE_REVIEWER_DOMINANCE)
                logger.warning(
                    f"Reviewer {reviewer_id} accounts for >{30}% of all reviews"
                )

    def save_parameter_version(
        self,
        parameters: Dict[str, Any],
        notes: str = ""
    ) -> ParameterVersion:
        """
        Save a versioned snapshot of parameters for rollback capability.
        """
        self.current_version += 1

        # Compute hash of parameters
        param_json = json.dumps(parameters, sort_keys=True, default=str)
        param_hash = hashlib.sha256(param_json.encode()).hexdigest()

        # Compute validation metrics
        avg_cred = 0.0
        if self.reviewer_credibility:
            avg_cred = sum(
                c.credibility_score for c in self.reviewer_credibility.values()
            ) / len(self.reviewer_credibility)

        outcome_sample = sum(
            c.total_decisions_with_outcomes for c in self.reviewer_credibility.values()
        )

        version = ParameterVersion(
            version=self.current_version,
            timestamp=datetime.now(),
            parameters_hash=param_hash,
            parameters_snapshot=parameters,
            avg_reviewer_credibility=avg_cred,
            outcome_sample_size=outcome_sample,
            validation_notes=notes,
        )

        self.parameter_versions.append(version)

        # Keep last 10 versions
        if len(self.parameter_versions) > 10:
            self.parameter_versions = self.parameter_versions[-10:]

        logger.info(
            f"Saved parameter version {self.current_version} "
            f"(hash={param_hash[:8]}, cred={avg_cred:.2f}, outcomes={outcome_sample})"
        )

        return version

    def rollback_to_version(self, version: int) -> Optional[Dict[str, Any]]:
        """
        Roll back to a previous parameter version.

        Returns the parameters from that version, or None if not found.
        """
        for v in self.parameter_versions:
            if v.version == version:
                logger.warning(f"🔙 Rolling back to parameter version {version}")
                self.detected_anomalies.append({
                    "type": "rollback",
                    "from_version": self.current_version,
                    "to_version": version,
                    "timestamp": datetime.now().isoformat(),
                })
                return v.parameters_snapshot

        logger.error(f"Version {version} not found for rollback")
        return None

    def get_last_good_version(self) -> Optional[ParameterVersion]:
        """
        Find the last version that passed validation checks.
        """
        for v in reversed(self.parameter_versions):
            if v.validated and v.avg_reviewer_credibility > 0.5:
                return v
        return None

    def detect_corruption(self, current_parameters: Dict[str, Any]) -> Optional[str]:
        """
        Detect if current parameters may be corrupted.

        Returns reason string if corruption suspected, None otherwise.
        """
        if not self.parameter_versions:
            return None

        # Check 1: Average reviewer credibility dropped significantly
        avg_cred = sum(
            c.credibility_score for c in self.reviewer_credibility.values()
        ) / max(1, len(self.reviewer_credibility))

        last_version = self.parameter_versions[-1]
        if avg_cred < last_version.avg_reviewer_credibility - 0.2:
            return f"Reviewer credibility dropped: {last_version.avg_reviewer_credibility:.2f} -> {avg_cred:.2f}"

        # Check 2: Too many flagged reviewers
        flagged_count = sum(1 for c in self.reviewer_credibility.values() if c.flagged_for_review)
        if flagged_count > len(self.reviewer_credibility) * 0.3:
            return f">{30}% of reviewers flagged ({flagged_count}/{len(self.reviewer_credibility)})"

        # Check 3: Large parameter change without proportional outcome data
        # (Would need to compare parameter values - implementation depends on structure)

        return None

    def get_safeguards_report(self) -> Dict[str, Any]:
        """Generate a report on current safeguard status."""
        flagged_reviewers = [
            c.to_dict() for c in self.reviewer_credibility.values()
            if c.flagged_for_review
        ]

        return {
            "reviewer_count": len(self.reviewer_credibility),
            "flagged_reviewers": flagged_reviewers,
            "recent_anomalies": self.detected_anomalies[-10:],
            "parameter_versions": len(self.parameter_versions),
            "current_version": self.current_version,
            "avg_credibility": sum(
                c.credibility_score for c in self.reviewer_credibility.values()
            ) / max(1, len(self.reviewer_credibility)),
            "total_outcome_data": sum(
                c.total_decisions_with_outcomes for c in self.reviewer_credibility.values()
            ),
            "settings": {
                "max_reviewer_influence": self.max_reviewer_influence,
                "outcome_wait_days": self.outcome_wait_days,
                "min_outcome_sample": self.min_outcome_sample,
                "min_credibility": self.min_credibility,
            }
        }

    def export_state(self) -> Dict[str, Any]:
        """Export state for persistence."""
        return {
            "reviewer_credibility": {
                k: v.to_dict() for k, v in self.reviewer_credibility.items()
            },
            "parameter_versions": [
                {
                    "version": v.version,
                    "timestamp": v.timestamp.isoformat(),
                    "parameters_hash": v.parameters_hash,
                    "avg_reviewer_credibility": v.avg_reviewer_credibility,
                    "outcome_sample_size": v.outcome_sample_size,
                    "validated": v.validated,
                    # Don't store full snapshot to save space
                }
                for v in self.parameter_versions
            ],
            "current_version": self.current_version,
            "detected_anomalies": self.detected_anomalies[-100:],
        }

    def _save_state(self):
        """Save state to disk."""
        if not self.state_path:
            return

        state = self.export_state()
        path = Path(self.state_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load state from disk."""
        if not self.state_path:
            return

        path = Path(self.state_path)
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            self.reviewer_credibility = {
                k: ReviewerCredibility.from_dict(v)
                for k, v in state.get("reviewer_credibility", {}).items()
            }
            self.current_version = state.get("current_version", 0)
            self.detected_anomalies = state.get("detected_anomalies", [])

            logger.info(
                f"Loaded safeguards state: "
                f"{len(self.reviewer_credibility)} reviewers, "
                f"version {self.current_version}"
            )
        except Exception as e:
            logger.error(f"Failed to load safeguards state: {e}")
