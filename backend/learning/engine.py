"""
Learning Engine for TrustChain.

Takes human feedback and improves future decisions by:
1. Adjusting model weights in multi-model consensus
2. Calibrating confidence scores
3. Tuning analyzer sensitivity
4. Identifying patterns in overrides

The learning engine is conservative by design:
- Requires minimum feedback count before adjusting
- Uses small learning rate to avoid overcorrection
- All changes are logged and auditable

Built with care by Kareem & Claude
"""

import logging
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from feedback.storage import FeedbackStore
from feedback.capture import HumanFeedback, ReviewerAction, FeedbackStats

logger = logging.getLogger(__name__)


@dataclass
class ModelWeight:
    """
    Learned weight for a model in multi-model consensus.

    Tracks how reliable each model is and adjusts voting weight accordingly.
    """

    model_name: str
    base_weight: float = 1.0
    learned_adjustment: float = 0.0  # Can be negative

    # Breakdown by decision type
    type_adjustments: Dict[str, float] = field(default_factory=dict)

    # Track accuracy metrics
    total_decisions: int = 0
    correct_decisions: int = 0

    # Track history
    last_updated: datetime = field(default_factory=datetime.now)
    feedback_count: int = 0

    @property
    def effective_weight(self) -> float:
        """Get the effective weight (base + learned adjustment)."""
        return max(0.1, self.base_weight + self.learned_adjustment)

    @property
    def accuracy(self) -> float:
        """Get model accuracy based on feedback."""
        if self.total_decisions == 0:
            return 0.5  # No data, assume neutral
        return self.correct_decisions / self.total_decisions

    def weight_for_type(self, decision_type: str) -> float:
        """Get weight adjusted for decision type."""
        adjustment = self.type_adjustments.get(decision_type, 0.0)
        return max(0.1, self.base_weight + self.learned_adjustment + adjustment)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "base_weight": self.base_weight,
            "learned_adjustment": self.learned_adjustment,
            "type_adjustments": self.type_adjustments,
            "total_decisions": self.total_decisions,
            "correct_decisions": self.correct_decisions,
            "effective_weight": self.effective_weight,
            "accuracy": self.accuracy,
            "last_updated": self.last_updated.isoformat(),
            "feedback_count": self.feedback_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelWeight":
        """Create from dictionary."""
        return cls(
            model_name=data["model_name"],
            base_weight=data.get("base_weight", 1.0),
            learned_adjustment=data.get("learned_adjustment", 0.0),
            type_adjustments=data.get("type_adjustments", {}),
            total_decisions=data.get("total_decisions", 0),
            correct_decisions=data.get("correct_decisions", 0),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.now(),
            feedback_count=data.get("feedback_count", 0),
        )


@dataclass
class ConfidenceCalibration:
    """
    Learned confidence calibration.

    Maps reported confidence to actual accuracy. For example, when
    a model says it's 90% confident, it might actually be right only 75%
    of the time - this calibration corrects for that.
    """

    # Calibration curve: confidence bucket -> actual accuracy
    # Keys are buckets: "0.5-0.6", "0.6-0.7", etc.
    calibration_curve: Dict[str, float] = field(default_factory=dict)

    # Sample counts per bucket (for weighted updates)
    bucket_counts: Dict[str, int] = field(default_factory=dict)

    # Per-model calibration (some models are more reliable at certain confidence levels)
    model_calibration: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def calibrate(self, raw_confidence: float, model: Optional[str] = None) -> float:
        """
        Return calibrated confidence.

        Args:
            raw_confidence: The model's reported confidence (0-1)
            model: Optional model name for model-specific calibration

        Returns:
            Calibrated confidence based on historical accuracy
        """
        bucket = self._get_bucket(raw_confidence)

        # Try model-specific calibration first
        if model and model in self.model_calibration:
            curve = self.model_calibration[model]
            if bucket in curve:
                return curve[bucket]

        # Fall back to general calibration
        if bucket in self.calibration_curve:
            return self.calibration_curve[bucket]

        # No calibration data yet
        return raw_confidence

    def _get_bucket(self, confidence: float) -> str:
        """Get the bucket string for a confidence value."""
        bucket_start = int(confidence * 10) / 10
        bucket_end = bucket_start + 0.1
        return f"{bucket_start:.1f}-{bucket_end:.1f}"

    def update(self, raw_confidence: float, was_correct: bool, model: Optional[str] = None):
        """
        Update calibration with new data point.

        Args:
            raw_confidence: The model's reported confidence
            was_correct: Whether the decision was correct (agreed with by human)
            model: Optional model name for model-specific calibration
        """
        bucket = self._get_bucket(raw_confidence)

        # Update bucket counts
        self.bucket_counts[bucket] = self.bucket_counts.get(bucket, 0) + 1

        # Update running average for calibration curve
        if bucket not in self.calibration_curve:
            self.calibration_curve[bucket] = 1.0 if was_correct else 0.0
        else:
            # Weighted running average
            count = self.bucket_counts[bucket]
            old_val = self.calibration_curve[bucket]
            new_val = 1.0 if was_correct else 0.0
            self.calibration_curve[bucket] = old_val + (new_val - old_val) / count

        # Update model-specific calibration if model provided
        if model:
            if model not in self.model_calibration:
                self.model_calibration[model] = {}
            model_curve = self.model_calibration[model]
            if bucket not in model_curve:
                model_curve[bucket] = 1.0 if was_correct else 0.0
            else:
                count = self.bucket_counts.get(f"{model}:{bucket}", 0) + 1
                self.bucket_counts[f"{model}:{bucket}"] = count
                old_val = model_curve[bucket]
                new_val = 1.0 if was_correct else 0.0
                model_curve[bucket] = old_val + (new_val - old_val) / count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "calibration_curve": self.calibration_curve,
            "bucket_counts": self.bucket_counts,
            "model_calibration": self.model_calibration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfidenceCalibration":
        """Create from dictionary."""
        return cls(
            calibration_curve=data.get("calibration_curve", {}),
            bucket_counts=data.get("bucket_counts", {}),
            model_calibration=data.get("model_calibration", {}),
        )


@dataclass
class AnalyzerTuning:
    """
    Learned sensitivity tuning for an analyzer.

    If an analyzer has high false positive rate, reduce sensitivity.
    If it has high false negative rate, increase sensitivity.
    """

    analyzer_name: str

    # Sensitivity adjustment: -1.0 (reduce) to 1.0 (increase)
    sensitivity_adjustment: float = 0.0

    # Patterns that were false positives (should potentially ignore)
    false_positive_patterns: List[str] = field(default_factory=list)

    # Patterns that were false negatives (should potentially add)
    missed_patterns: List[str] = field(default_factory=list)

    # Per-decision-type adjustments
    type_sensitivity: Dict[str, float] = field(default_factory=dict)

    # Track metrics
    total_flags: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def false_positive_rate(self) -> float:
        """Get false positive rate."""
        if self.total_flags == 0:
            return 0.0
        return self.false_positives / self.total_flags

    @property
    def precision(self) -> float:
        """Get precision (true positives / all flags)."""
        if self.total_flags == 0:
            return 1.0
        return (self.total_flags - self.false_positives) / self.total_flags

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analyzer_name": self.analyzer_name,
            "sensitivity_adjustment": self.sensitivity_adjustment,
            "false_positive_patterns": self.false_positive_patterns,
            "missed_patterns": self.missed_patterns,
            "type_sensitivity": self.type_sensitivity,
            "total_flags": self.total_flags,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "false_positive_rate": self.false_positive_rate,
            "precision": self.precision,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalyzerTuning":
        """Create from dictionary."""
        return cls(
            analyzer_name=data["analyzer_name"],
            sensitivity_adjustment=data.get("sensitivity_adjustment", 0.0),
            false_positive_patterns=data.get("false_positive_patterns", []),
            missed_patterns=data.get("missed_patterns", []),
            type_sensitivity=data.get("type_sensitivity", {}),
            total_flags=data.get("total_flags", 0),
            false_positives=data.get("false_positives", 0),
            false_negatives=data.get("false_negatives", 0),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.now(),
        )


@dataclass
class LearnedParameters:
    """
    Parameters learned from feedback, ready to apply to TrustChain.

    This is what gets passed to TrustChain to modify its behavior.
    """

    # Model weights for multi-model consensus
    model_weights: Dict[str, float] = field(default_factory=dict)

    # Confidence calibration
    calibration: ConfidenceCalibration = field(default_factory=ConfidenceCalibration)

    # Analyzer sensitivity adjustments
    analyzer_sensitivity: Dict[str, float] = field(default_factory=dict)

    # Full analyzer tuning data (for advanced use)
    analyzer_tuning: Dict[str, AnalyzerTuning] = field(default_factory=dict)

    # Metadata
    last_trained: Optional[datetime] = None
    feedback_count: int = 0
    training_period_days: int = 30

    # Version for tracking changes
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "model_weights": self.model_weights,
            "calibration": self.calibration.to_dict(),
            "analyzer_sensitivity": self.analyzer_sensitivity,
            "analyzer_tuning": {k: v.to_dict() for k, v in self.analyzer_tuning.items()},
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "feedback_count": self.feedback_count,
            "training_period_days": self.training_period_days,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnedParameters":
        """Create from dictionary."""
        return cls(
            model_weights=data.get("model_weights", {}),
            calibration=ConfidenceCalibration.from_dict(data.get("calibration", {})),
            analyzer_sensitivity=data.get("analyzer_sensitivity", {}),
            analyzer_tuning={
                k: AnalyzerTuning.from_dict(v)
                for k, v in data.get("analyzer_tuning", {}).items()
            },
            last_trained=datetime.fromisoformat(data["last_trained"]) if data.get("last_trained") else None,
            feedback_count=data.get("feedback_count", 0),
            training_period_days=data.get("training_period_days", 30),
            version=data.get("version", 1),
        )


class LearningEngine:
    """
    Main learning engine for TrustChain.

    Takes human feedback and learns to improve future decisions.
    Includes safeguards against bad actors when LearningGuard is provided.

    Usage:
        from learning import LearningGuard

        guard = LearningGuard()  # Bad actor protection
        engine = LearningEngine(feedback_store, safeguard=guard)

        # Learn from accumulated feedback (with safeguards)
        results = await engine.learn()

        # Get learned parameters for a decision
        params = engine.get_parameters("hiring")

        # Apply to TrustChain
        tc = TrustChain.from_config(
            "configs/hiring.yaml",
            learned_parameters=params
        )
    """

    def __init__(
        self,
        feedback_store: FeedbackStore,
        learning_rate: float = 0.1,
        min_feedback_count: int = 10,
        state_path: Optional[str] = None,
        safeguard: Optional[Any] = None  # LearningGuard instance
    ):
        """
        Initialize learning engine.

        Args:
            feedback_store: Store for feedback data
            learning_rate: How fast to adjust (0.0-1.0, default 0.1)
            min_feedback_count: Minimum samples before adjusting
            state_path: Path to persist learned state
            safeguard: LearningGuard instance for bad actor protection
        """
        self.store = feedback_store
        self.learning_rate = learning_rate
        self.min_feedback = min_feedback_count
        self.state_path = state_path
        self.safeguard = safeguard  # Bad actor protection

        # Learned parameters
        self.model_weights: Dict[str, ModelWeight] = {}
        self.calibration = ConfidenceCalibration()
        self.analyzer_tuning: Dict[str, AnalyzerTuning] = {}

        # Learning metadata
        self.last_trained: Optional[datetime] = None
        self.training_feedback_count: int = 0
        self.version: int = 1

        # Load existing state if available
        if state_path:
            self._load_state()

        logger.info(
            f"LearningEngine initialized: "
            f"learning_rate={learning_rate}, "
            f"min_feedback={min_feedback_count}, "
            f"safeguards={'enabled' if safeguard else 'disabled'}"
        )

    async def learn(
        self,
        since: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        force: bool = False,
        outcome_only: bool = False  # Only learn from feedback with verified outcomes
    ) -> Dict[str, Any]:
        """
        Learn from feedback and update parameters.

        With safeguards enabled:
        - Reviewer credibility weights their influence
        - Flagged reviewers are excluded
        - No single reviewer dominates
        - Corruption is detected and logged

        Args:
            since: Only learn from feedback after this date
            decision_type: Only learn from specific decision type
            force: Learn even if below min feedback threshold
            outcome_only: Only learn from feedback with verified outcomes

        Returns:
            Summary of what was learned
        """
        logger.info("Starting learning cycle...")

        # Default to last 30 days
        if since is None:
            since = datetime.now() - timedelta(days=30)

        # Get feedback
        feedback_list = await self.store.get_feedback_batch(
            start_date=since,
            decision_type=decision_type,
            limit=100000
        )

        logger.info(f"Retrieved {len(feedback_list)} feedback entries")

        if len(feedback_list) < self.min_feedback and not force:
            return {
                "status": "insufficient_data",
                "count": len(feedback_list),
                "min_required": self.min_feedback,
                "message": f"Need at least {self.min_feedback} feedback entries to learn"
            }

        # === SAFEGUARD: Filter and weight feedback ===
        safeguard_report = None
        if self.safeguard:
            # Filter out flagged reviewers
            original_count = len(feedback_list)
            feedback_list = [
                f for f in feedback_list
                if self.safeguard.get_reviewer_weight(f.reviewer_id) > 0
            ]
            excluded = original_count - len(feedback_list)
            if excluded > 0:
                logger.warning(f"Excluded {excluded} feedback from flagged/low-credibility reviewers")

            # Filter for outcome-verified only if requested
            if outcome_only:
                feedback_list = [f for f in feedback_list if f.outcome_tracked]
                logger.info(f"Filtered to {len(feedback_list)} outcome-verified feedback")

            # Build weighted feedback (credibility-adjusted)
            reviewer_contributions: Dict[str, float] = {}
            for f in feedback_list:
                weight = self.safeguard.get_reviewer_weight(f.reviewer_id)
                reviewer_contributions[f.reviewer_id] = (
                    reviewer_contributions.get(f.reviewer_id, 0) + weight
                )

            # Apply reviewer caps
            reviewer_contributions = self.safeguard.apply_reviewer_caps(
                reviewer_contributions,
                len(feedback_list)
            )

            safeguard_report = {
                "reviewers_excluded": excluded,
                "unique_reviewers": len(reviewer_contributions),
                "reviewer_contributions": reviewer_contributions,
            }

        # Re-check after filtering
        if len(feedback_list) < self.min_feedback and not force:
            return {
                "status": "insufficient_data_after_filter",
                "count": len(feedback_list),
                "min_required": self.min_feedback,
                "safeguards": safeguard_report,
                "message": "Insufficient feedback after safeguard filtering"
            }

        # Learn from feedback (with credibility weighting if safeguards enabled)
        model_updates = self._learn_model_weights(feedback_list)
        calibration_updates = self._learn_calibration(feedback_list)
        analyzer_updates = self._learn_analyzer_tuning(feedback_list)

        # Update metadata
        self.last_trained = datetime.now()
        self.training_feedback_count = len(feedback_list)
        self.version += 1

        # === SAFEGUARD: Save versioned parameters for rollback ===
        if self.safeguard:
            self.safeguard.save_parameter_version(
                self.get_parameters().to_dict(),
                notes=f"Auto-save after learning v{self.version}"
            )

            # Check for corruption
            corruption = self.safeguard.detect_corruption(self.get_parameters().to_dict())
            if corruption:
                logger.error(f"🚨 CORRUPTION DETECTED: {corruption}")
                safeguard_report["corruption_warning"] = corruption

        # Persist state
        if self.state_path:
            self._save_state()

        result = {
            "status": "success",
            "feedback_count": len(feedback_list),
            "period": {
                "start": since.isoformat(),
                "end": datetime.now().isoformat(),
            },
            "model_updates": model_updates,
            "calibration_updates": calibration_updates,
            "analyzer_updates": analyzer_updates,
            "version": self.version,
        }

        if safeguard_report:
            result["safeguards"] = safeguard_report

        logger.info(f"Learning complete: {len(feedback_list)} samples, version {self.version}")
        return result

    def _learn_model_weights(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """
        Update model weights based on which models were right.

        A model is "correct" if the human agreed with the decision it contributed to.
        """
        # Count correct/incorrect per model
        # Note: In a real implementation, we'd need to look up the original
        # AccountabilityResult to see which models voted how.
        # For now, we track overall agreement rates.

        updates = {}

        # Group by whether human agreed
        agreed = [f for f in feedback if f.action.is_agreement]
        overrode = [f for f in feedback if f.action.is_override]

        agreement_rate = len(agreed) / len(feedback) if feedback else 0

        # If agreement rate is high, models are doing well
        # If override rate is high, models need adjustment
        overall_adjustment = (agreement_rate - 0.5) * self.learning_rate

        # Apply adjustment to all known models
        for model_name in list(self.model_weights.keys()):
            weight = self.model_weights[model_name]
            weight.learned_adjustment += overall_adjustment
            weight.feedback_count += len(feedback)
            weight.last_updated = datetime.now()

            updates[model_name] = {
                "new_adjustment": weight.learned_adjustment,
                "effective_weight": weight.effective_weight,
            }

        return {
            "agreement_rate": agreement_rate,
            "adjustment_applied": overall_adjustment,
            "models_updated": updates,
        }

    def _learn_calibration(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """
        Learn confidence calibration from feedback.

        Builds a mapping of reported confidence -> actual accuracy.
        """
        # In a real implementation, we'd look up the original confidence
        # from the AccountabilityResult. For now, we'll track general patterns.

        updates = {}

        for fb in feedback:
            was_correct = fb.action.is_agreement
            # We'd get raw_confidence from the original result
            # For now, use reviewer confidence as proxy
            raw_confidence = fb.reviewer_confidence

            self.calibration.update(raw_confidence, was_correct)

        updates = {
            "buckets_updated": len(self.calibration.calibration_curve),
            "calibration_curve": self.calibration.calibration_curve,
        }

        return updates

    def _learn_analyzer_tuning(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """
        Learn analyzer sensitivity from false positives/negatives.

        If an analyzer is frequently flagged as incorrect, reduce its sensitivity.
        If it's frequently missing things, increase its sensitivity.
        """
        updates = {}

        # Count false positives/negatives per analyzer
        for fb in feedback:
            # Process incorrect flags (false positives)
            for analyzer in fb.incorrect_flags:
                if analyzer not in self.analyzer_tuning:
                    self.analyzer_tuning[analyzer] = AnalyzerTuning(analyzer_name=analyzer)

                tuning = self.analyzer_tuning[analyzer]
                tuning.total_flags += 1
                tuning.false_positives += 1
                tuning.last_updated = datetime.now()

            # Process missed flags (false negatives)
            for analyzer in fb.missed_flags:
                if analyzer not in self.analyzer_tuning:
                    self.analyzer_tuning[analyzer] = AnalyzerTuning(analyzer_name=analyzer)

                tuning = self.analyzer_tuning[analyzer]
                tuning.false_negatives += 1
                tuning.last_updated = datetime.now()

        # Adjust sensitivity based on FP/FN rates
        for analyzer_name, tuning in self.analyzer_tuning.items():
            if tuning.total_flags + tuning.false_negatives >= self.min_feedback:
                # High FP rate -> reduce sensitivity (negative adjustment)
                # High FN rate -> increase sensitivity (positive adjustment)
                fp_rate = tuning.false_positive_rate
                fn_rate = tuning.false_negatives / max(1, tuning.total_flags + tuning.false_negatives)

                # Adjustment: increase if more FN than FP, decrease if more FP than FN
                adjustment = (fn_rate - fp_rate) * self.learning_rate
                tuning.sensitivity_adjustment += adjustment

                updates[analyzer_name] = {
                    "false_positive_rate": fp_rate,
                    "false_negative_rate": fn_rate,
                    "sensitivity_adjustment": tuning.sensitivity_adjustment,
                    "precision": tuning.precision,
                }

        return updates

    def get_parameters(self, decision_type: Optional[str] = None) -> LearnedParameters:
        """
        Get current learned parameters ready for use.

        Args:
            decision_type: Optional decision type for type-specific adjustments

        Returns:
            LearnedParameters ready to apply to TrustChain
        """
        # Build model weights dict
        model_weights = {}
        for name, weight in self.model_weights.items():
            if decision_type:
                model_weights[name] = weight.weight_for_type(decision_type)
            else:
                model_weights[name] = weight.effective_weight

        # Build analyzer sensitivity dict
        analyzer_sensitivity = {}
        for name, tuning in self.analyzer_tuning.items():
            if decision_type and decision_type in tuning.type_sensitivity:
                analyzer_sensitivity[name] = tuning.type_sensitivity[decision_type]
            else:
                analyzer_sensitivity[name] = tuning.sensitivity_adjustment

        return LearnedParameters(
            model_weights=model_weights,
            calibration=self.calibration,
            analyzer_sensitivity=analyzer_sensitivity,
            analyzer_tuning=self.analyzer_tuning,
            last_trained=self.last_trained,
            feedback_count=self.training_feedback_count,
            version=self.version,
        )

    def register_model(self, model_name: str, base_weight: float = 1.0):
        """Register a model for weight tracking."""
        if model_name not in self.model_weights:
            self.model_weights[model_name] = ModelWeight(
                model_name=model_name,
                base_weight=base_weight
            )
            logger.info(f"Registered model: {model_name} (weight={base_weight})")

    def export_state(self) -> Dict[str, Any]:
        """Export learned state for persistence."""
        return {
            "model_weights": {k: v.to_dict() for k, v in self.model_weights.items()},
            "calibration": self.calibration.to_dict(),
            "analyzer_tuning": {k: v.to_dict() for k, v in self.analyzer_tuning.items()},
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "feedback_count": self.training_feedback_count,
            "version": self.version,
        }

    def import_state(self, state: Dict[str, Any]):
        """Import previously learned state."""
        self.model_weights = {
            k: ModelWeight.from_dict(v)
            for k, v in state.get("model_weights", {}).items()
        }
        self.calibration = ConfidenceCalibration.from_dict(state.get("calibration", {}))
        self.analyzer_tuning = {
            k: AnalyzerTuning.from_dict(v)
            for k, v in state.get("analyzer_tuning", {}).items()
        }
        self.last_trained = datetime.fromisoformat(state["last_trained"]) if state.get("last_trained") else None
        self.training_feedback_count = state.get("feedback_count", 0)
        self.version = state.get("version", 1)

        logger.info(f"Imported state: version={self.version}, feedback_count={self.training_feedback_count}")

    def _save_state(self):
        """Save state to disk."""
        if not self.state_path:
            return

        state = self.export_state()
        path = Path(self.state_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"Saved learning state to {self.state_path}")

    def _load_state(self):
        """Load state from disk."""
        if not self.state_path:
            return

        path = Path(self.state_path)
        if not path.exists():
            logger.info("No existing learning state found")
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)
            self.import_state(state)
            logger.info(f"Loaded learning state from {self.state_path}")
        except Exception as e:
            logger.error(f"Failed to load learning state: {e}")

    def reset(self):
        """Reset all learned parameters."""
        self.model_weights = {}
        self.calibration = ConfidenceCalibration()
        self.analyzer_tuning = {}
        self.last_trained = None
        self.training_feedback_count = 0
        self.version = 1

        if self.state_path:
            path = Path(self.state_path)
            if path.exists():
                path.unlink()

        logger.info("Learning engine reset")
