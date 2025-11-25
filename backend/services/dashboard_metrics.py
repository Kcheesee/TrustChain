"""
TrustChain Dashboard Metrics Service

Aggregates real-time metrics for the dashboard including:
- Decision throughput and outcomes
- Fairness scores over time
- Reviewer activity and credibility
- System health indicators

Usage:
    metrics = DashboardMetrics()
    metrics.record_decision(result)
    summary = metrics.get_summary()

Built with care by Kareem & Claude
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class TimeWindow(str, Enum):
    """Time windows for metric aggregation."""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


@dataclass
class DecisionMetric:
    """A single decision record for metrics."""
    result_id: str
    case_id: str
    decision_type: str
    final_decision: str
    confidence: float
    requires_review: bool
    fairness_score: Optional[float]
    biases_detected: List[str]
    timestamp: datetime
    latency_ms: Optional[int] = None


@dataclass
class ReviewerMetric:
    """Reviewer activity metric."""
    reviewer_id: str
    action: str
    result_id: str
    timestamp: datetime
    is_override: bool = False


@dataclass
class MetricsSummary:
    """Aggregated metrics summary."""
    # Counts
    total_decisions: int = 0
    decisions_approved: int = 0
    decisions_denied: int = 0
    decisions_needs_review: int = 0

    # Rates
    approval_rate: float = 0.0
    review_rate: float = 0.0

    # Confidence
    avg_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0

    # Fairness
    avg_fairness_score: float = 0.0
    decisions_with_bias: int = 0
    bias_rate: float = 0.0
    common_biases: Dict[str, int] = field(default_factory=dict)

    # Throughput
    decisions_per_minute: float = 0.0
    avg_latency_ms: float = 0.0

    # By type
    by_decision_type: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Time range
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class DashboardMetrics:
    """
    Real-time metrics aggregation for the TrustChain dashboard.

    Maintains rolling windows of metrics and provides aggregated summaries
    for visualization.
    """

    def __init__(self, max_history_hours: int = 24):
        """
        Initialize metrics tracker.

        Args:
            max_history_hours: How many hours of history to keep
        """
        self.max_history = timedelta(hours=max_history_hours)

        # Rolling decision metrics
        self._decisions: List[DecisionMetric] = []

        # Rolling reviewer metrics
        self._reviewer_activity: List[ReviewerMetric] = []

        # Quick lookup counters (reset periodically)
        self._decision_counts: Dict[str, int] = defaultdict(int)
        self._bias_counts: Dict[str, int] = defaultdict(int)

        # Time series data for charts (minute-level granularity)
        self._time_series: Dict[str, List[Dict[str, Any]]] = {
            "decisions": [],
            "fairness": [],
            "confidence": [],
        }

    def record_decision(self, result: Any) -> None:
        """
        Record a decision for metrics tracking.

        Args:
            result: AccountabilityResult or dict with decision data
        """
        # Extract data
        if hasattr(result, 'to_dict'):
            data = result.to_dict()
        else:
            data = result

        # Extract fairness data if present
        fairness_score = None
        biases_detected = []
        for ar in data.get("analysis_results", []):
            if ar.get("analyzer_name") == "counterfactual_fairness":
                details = ar.get("details", {})
                fairness_score = details.get("fairness_score")
                biases_detected = details.get("biases_detected", [])
                break

        metric = DecisionMetric(
            result_id=data.get("result_id", ""),
            case_id=data.get("case_id", ""),
            decision_type=data.get("decision_type", "unknown"),
            final_decision=data.get("final_decision", "unknown"),
            confidence=data.get("overall_confidence", 0.0),
            requires_review=data.get("requires_human_review", False),
            fairness_score=fairness_score,
            biases_detected=biases_detected,
            timestamp=datetime.now(),
            latency_ms=data.get("latency_ms")
        )

        self._decisions.append(metric)

        # Update counters
        self._decision_counts[metric.final_decision] += 1
        self._decision_counts[f"type:{metric.decision_type}"] += 1

        for bias in biases_detected:
            self._bias_counts[bias] += 1

        # Update time series
        self._update_time_series(metric)

        # Prune old data
        self._prune_old_data()

        logger.debug(f"Recorded decision metric: {metric.result_id}")

    def record_reviewer_activity(
        self,
        reviewer_id: str,
        action: str,
        result_id: str,
        is_override: bool = False
    ) -> None:
        """
        Record reviewer activity.

        Args:
            reviewer_id: Reviewer identifier
            action: Action taken (agree, override_approve, override_deny, escalate)
            result_id: Related decision result ID
            is_override: Whether this was an override
        """
        metric = ReviewerMetric(
            reviewer_id=reviewer_id,
            action=action,
            result_id=result_id,
            timestamp=datetime.now(),
            is_override=is_override
        )

        self._reviewer_activity.append(metric)
        self._prune_old_data()

        logger.debug(f"Recorded reviewer activity: {reviewer_id} - {action}")

    def get_summary(
        self,
        window: TimeWindow = TimeWindow.HOUR,
        decision_type: Optional[str] = None
    ) -> MetricsSummary:
        """
        Get aggregated metrics summary.

        Args:
            window: Time window for aggregation
            decision_type: Optional filter by decision type

        Returns:
            MetricsSummary with aggregated data
        """
        # Determine time range
        now = datetime.now()
        if window == TimeWindow.MINUTE:
            start = now - timedelta(minutes=1)
        elif window == TimeWindow.HOUR:
            start = now - timedelta(hours=1)
        elif window == TimeWindow.DAY:
            start = now - timedelta(days=1)
        else:  # WEEK
            start = now - timedelta(weeks=1)

        # Filter decisions
        decisions = [
            d for d in self._decisions
            if d.timestamp >= start
            and (decision_type is None or d.decision_type == decision_type)
        ]

        if not decisions:
            return MetricsSummary(window_start=start, window_end=now)

        # Calculate metrics
        total = len(decisions)
        approved = sum(1 for d in decisions if d.final_decision == "approved")
        denied = sum(1 for d in decisions if d.final_decision == "denied")
        needs_review = sum(1 for d in decisions if d.final_decision == "needs_review")

        confidences = [d.confidence for d in decisions]
        fairness_scores = [d.fairness_score for d in decisions if d.fairness_score is not None]

        decisions_with_bias = sum(1 for d in decisions if d.biases_detected)

        # Count biases
        bias_counts: Dict[str, int] = defaultdict(int)
        for d in decisions:
            for bias in d.biases_detected:
                bias_counts[bias] += 1

        # Calculate latency
        latencies = [d.latency_ms for d in decisions if d.latency_ms is not None]

        # Calculate by decision type
        by_type: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0, "approved": 0, "denied": 0, "needs_review": 0
        })
        for d in decisions:
            by_type[d.decision_type]["total"] += 1
            if d.final_decision == "approved":
                by_type[d.decision_type]["approved"] += 1
            elif d.final_decision == "denied":
                by_type[d.decision_type]["denied"] += 1
            elif d.final_decision == "needs_review":
                by_type[d.decision_type]["needs_review"] += 1

        # Time span in minutes for throughput calculation
        time_span_minutes = max((now - start).total_seconds() / 60, 1)

        return MetricsSummary(
            total_decisions=total,
            decisions_approved=approved,
            decisions_denied=denied,
            decisions_needs_review=needs_review,
            approval_rate=approved / total if total > 0 else 0.0,
            review_rate=needs_review / total if total > 0 else 0.0,
            avg_confidence=statistics.mean(confidences) if confidences else 0.0,
            min_confidence=min(confidences) if confidences else 0.0,
            max_confidence=max(confidences) if confidences else 0.0,
            avg_fairness_score=statistics.mean(fairness_scores) if fairness_scores else 0.0,
            decisions_with_bias=decisions_with_bias,
            bias_rate=decisions_with_bias / total if total > 0 else 0.0,
            common_biases=dict(sorted(bias_counts.items(), key=lambda x: -x[1])[:5]),
            decisions_per_minute=total / time_span_minutes,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            by_decision_type=dict(by_type),
            window_start=start,
            window_end=now
        )

    def get_time_series(
        self,
        metric_type: str,
        window: TimeWindow = TimeWindow.HOUR,
        granularity_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for charts.

        Args:
            metric_type: Type of metric (decisions, fairness, confidence)
            window: Time window
            granularity_minutes: Data point interval in minutes

        Returns:
            List of time series data points
        """
        now = datetime.now()
        if window == TimeWindow.MINUTE:
            start = now - timedelta(minutes=1)
            granularity_minutes = 1
        elif window == TimeWindow.HOUR:
            start = now - timedelta(hours=1)
        elif window == TimeWindow.DAY:
            start = now - timedelta(days=1)
            granularity_minutes = 60  # Hourly for day view
        else:  # WEEK
            start = now - timedelta(weeks=1)
            granularity_minutes = 360  # 6-hour intervals for week

        # Generate time buckets
        buckets: Dict[datetime, List[DecisionMetric]] = defaultdict(list)

        for decision in self._decisions:
            if decision.timestamp >= start:
                # Round to nearest bucket
                bucket_time = decision.timestamp.replace(
                    minute=(decision.timestamp.minute // granularity_minutes) * granularity_minutes,
                    second=0,
                    microsecond=0
                )
                buckets[bucket_time].append(decision)

        # Build time series
        series = []
        current = start.replace(
            minute=(start.minute // granularity_minutes) * granularity_minutes,
            second=0,
            microsecond=0
        )

        while current <= now:
            decisions_in_bucket = buckets.get(current, [])

            if metric_type == "decisions":
                series.append({
                    "timestamp": current.isoformat(),
                    "total": len(decisions_in_bucket),
                    "approved": sum(1 for d in decisions_in_bucket if d.final_decision == "approved"),
                    "denied": sum(1 for d in decisions_in_bucket if d.final_decision == "denied"),
                    "needs_review": sum(1 for d in decisions_in_bucket if d.final_decision == "needs_review"),
                })
            elif metric_type == "fairness":
                scores = [d.fairness_score for d in decisions_in_bucket if d.fairness_score is not None]
                series.append({
                    "timestamp": current.isoformat(),
                    "avg_fairness": statistics.mean(scores) if scores else None,
                    "min_fairness": min(scores) if scores else None,
                    "max_fairness": max(scores) if scores else None,
                    "count": len(scores),
                })
            elif metric_type == "confidence":
                confidences = [d.confidence for d in decisions_in_bucket]
                series.append({
                    "timestamp": current.isoformat(),
                    "avg_confidence": statistics.mean(confidences) if confidences else None,
                    "min_confidence": min(confidences) if confidences else None,
                    "max_confidence": max(confidences) if confidences else None,
                    "count": len(confidences),
                })

            current += timedelta(minutes=granularity_minutes)

        return series

    def get_reviewer_summary(
        self,
        window: TimeWindow = TimeWindow.DAY
    ) -> Dict[str, Any]:
        """
        Get reviewer activity summary.

        Args:
            window: Time window for aggregation

        Returns:
            Dictionary with reviewer activity metrics
        """
        now = datetime.now()
        if window == TimeWindow.HOUR:
            start = now - timedelta(hours=1)
        elif window == TimeWindow.DAY:
            start = now - timedelta(days=1)
        else:
            start = now - timedelta(weeks=1)

        # Filter activity
        activity = [a for a in self._reviewer_activity if a.timestamp >= start]

        # Aggregate by reviewer
        by_reviewer: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_actions": 0,
            "agrees": 0,
            "overrides": 0,
            "escalations": 0,
            "override_rate": 0.0,
        })

        for a in activity:
            reviewer = by_reviewer[a.reviewer_id]
            reviewer["total_actions"] += 1

            if a.action == "agree":
                reviewer["agrees"] += 1
            elif a.is_override:
                reviewer["overrides"] += 1
            elif a.action == "escalate":
                reviewer["escalations"] += 1

        # Calculate override rates
        for reviewer_data in by_reviewer.values():
            total = reviewer_data["total_actions"]
            if total > 0:
                reviewer_data["override_rate"] = reviewer_data["overrides"] / total

        # Action distribution
        action_counts: Dict[str, int] = defaultdict(int)
        for a in activity:
            action_counts[a.action] += 1

        return {
            "total_activity": len(activity),
            "unique_reviewers": len(by_reviewer),
            "total_overrides": sum(1 for a in activity if a.is_override),
            "override_rate": sum(1 for a in activity if a.is_override) / len(activity) if activity else 0.0,
            "by_reviewer": dict(by_reviewer),
            "action_distribution": dict(action_counts),
            "window_start": start.isoformat(),
            "window_end": now.isoformat(),
        }

    def get_bias_breakdown(
        self,
        window: TimeWindow = TimeWindow.DAY
    ) -> Dict[str, Any]:
        """
        Get detailed bias detection breakdown.

        Args:
            window: Time window

        Returns:
            Dictionary with bias breakdown data
        """
        now = datetime.now()
        if window == TimeWindow.HOUR:
            start = now - timedelta(hours=1)
        elif window == TimeWindow.DAY:
            start = now - timedelta(days=1)
        else:
            start = now - timedelta(weeks=1)

        decisions = [d for d in self._decisions if d.timestamp >= start]

        # Count biases
        bias_counts: Dict[str, int] = defaultdict(int)
        bias_by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        decisions_tested = 0
        decisions_with_bias = 0

        for d in decisions:
            if d.fairness_score is not None:
                decisions_tested += 1
                if d.biases_detected:
                    decisions_with_bias += 1

                for bias in d.biases_detected:
                    bias_counts[bias] += 1
                    bias_by_type[d.decision_type][bias] += 1

        return {
            "decisions_tested": decisions_tested,
            "decisions_with_bias": decisions_with_bias,
            "bias_detection_rate": decisions_with_bias / decisions_tested if decisions_tested > 0 else 0.0,
            "bias_counts": dict(sorted(bias_counts.items(), key=lambda x: -x[1])),
            "bias_by_decision_type": {k: dict(v) for k, v in bias_by_type.items()},
            "window_start": start.isoformat(),
            "window_end": now.isoformat(),
        }

    def _update_time_series(self, metric: DecisionMetric) -> None:
        """Update time series data with new metric."""
        # This is handled dynamically in get_time_series
        pass

    def _prune_old_data(self) -> None:
        """Remove data older than max_history."""
        cutoff = datetime.now() - self.max_history

        self._decisions = [d for d in self._decisions if d.timestamp >= cutoff]
        self._reviewer_activity = [a for a in self._reviewer_activity if a.timestamp >= cutoff]


# Global metrics instance
dashboard_metrics = DashboardMetrics()
