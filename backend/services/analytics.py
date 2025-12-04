"""
TrustChain Analytics Service

Provides advanced analytics and reporting capabilities:
- Decision trend analysis
- Fairness reports
- Reviewer performance metrics
- Export capabilities

Usage:
    from services.analytics import analytics_service

    report = analytics_service.generate_fairness_report(window="day")
    trends = analytics_service.get_decision_trends(days=7)

Built with care by Kareem & Claude
"""

import logging
import csv
import json
import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Export format options."""
    JSON = "json"
    CSV = "csv"


@dataclass
class DecisionTrend:
    """Decision trend data point."""
    date: str
    total: int
    approved: int
    denied: int
    needs_review: int
    approval_rate: float
    avg_confidence: float


@dataclass
class FairnessReport:
    """Comprehensive fairness report."""
    report_id: str
    generated_at: str
    period_start: str
    period_end: str
    summary: Dict[str, Any]
    bias_breakdown: Dict[str, Any]
    recommendations: List[str]
    decision_type_analysis: Dict[str, Dict[str, Any]]


@dataclass
class ReviewerPerformance:
    """Reviewer performance metrics."""
    reviewer_id: str
    total_reviews: int
    agreements: int
    overrides: int
    escalations: int
    agreement_rate: float
    override_rate: float
    avg_response_time_seconds: Optional[float] = None
    accuracy_score: Optional[float] = None


@dataclass
class AnalyticsReport:
    """Full analytics report."""
    report_id: str
    generated_at: str
    period: str
    decision_summary: Dict[str, Any]
    fairness_summary: Dict[str, Any]
    reviewer_summary: Dict[str, Any]
    trends: List[DecisionTrend]
    alerts: List[Dict[str, Any]]


class AnalyticsService:
    """
    Advanced analytics and reporting service.

    Provides comprehensive analytics on decision patterns,
    fairness metrics, and reviewer performance.
    """

    def __init__(self, dashboard_metrics=None):
        """
        Initialize analytics service.

        Args:
            dashboard_metrics: Optional DashboardMetrics instance for data
        """
        self._metrics = dashboard_metrics
        self._report_counter = 0

    def set_metrics_source(self, dashboard_metrics):
        """Set the metrics data source."""
        self._metrics = dashboard_metrics

    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        self._report_counter += 1
        return f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._report_counter}"

    def get_decision_trends(
        self,
        days: int = 7,
        decision_type: Optional[str] = None
    ) -> List[DecisionTrend]:
        """
        Get decision trends over time.

        Args:
            days: Number of days to analyze
            decision_type: Optional filter by decision type

        Returns:
            List of daily trend data points
        """
        if not self._metrics:
            return []

        trends = []
        now = datetime.now()

        for day_offset in range(days, 0, -1):
            date = now - timedelta(days=day_offset)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)

            # Filter decisions for this day
            day_decisions = [
                d for d in self._metrics._decisions
                if date_start <= d.timestamp < date_end
                and (decision_type is None or d.decision_type == decision_type)
            ]

            if day_decisions:
                total = len(day_decisions)
                approved = sum(1 for d in day_decisions if d.final_decision == "approved")
                denied = sum(1 for d in day_decisions if d.final_decision == "denied")
                needs_review = sum(1 for d in day_decisions if d.final_decision == "needs_review")
                confidences = [d.confidence for d in day_decisions]

                trends.append(DecisionTrend(
                    date=date_start.strftime("%Y-%m-%d"),
                    total=total,
                    approved=approved,
                    denied=denied,
                    needs_review=needs_review,
                    approval_rate=approved / total if total > 0 else 0.0,
                    avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0
                ))
            else:
                trends.append(DecisionTrend(
                    date=date_start.strftime("%Y-%m-%d"),
                    total=0,
                    approved=0,
                    denied=0,
                    needs_review=0,
                    approval_rate=0.0,
                    avg_confidence=0.0
                ))

        return trends

    def generate_fairness_report(
        self,
        window_days: int = 1
    ) -> FairnessReport:
        """
        Generate comprehensive fairness report.

        Args:
            window_days: Time window in days

        Returns:
            FairnessReport with analysis and recommendations
        """
        now = datetime.now()
        start = now - timedelta(days=window_days)

        # Get relevant decisions
        decisions = []
        if self._metrics:
            decisions = [
                d for d in self._metrics._decisions
                if d.timestamp >= start
            ]

        # Analyze fairness
        tested = [d for d in decisions if d.fairness_score is not None]
        with_bias = [d for d in tested if d.biases_detected]

        # Bias type breakdown
        bias_counts: Dict[str, int] = defaultdict(int)
        for d in with_bias:
            for bias in d.biases_detected:
                bias_counts[bias] += 1

        # By decision type
        by_type: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "tested": 0, "with_bias": 0, "avg_fairness": 0.0, "biases": {}
        })

        for d in tested:
            dt = by_type[d.decision_type]
            dt["tested"] += 1
            if d.biases_detected:
                dt["with_bias"] += 1
            for bias in d.biases_detected:
                if bias not in dt["biases"]:
                    dt["biases"][bias] = 0
                dt["biases"][bias] += 1

        # Calculate avg fairness per type
        for dt_name in by_type:
            type_decisions = [d for d in tested if d.decision_type == dt_name]
            scores = [d.fairness_score for d in type_decisions if d.fairness_score]
            by_type[dt_name]["avg_fairness"] = sum(scores) / len(scores) if scores else 0.0

        # Generate recommendations
        recommendations = self._generate_fairness_recommendations(
            len(tested),
            len(with_bias),
            dict(bias_counts)
        )

        return FairnessReport(
            report_id=self._generate_report_id(),
            generated_at=now.isoformat(),
            period_start=start.isoformat(),
            period_end=now.isoformat(),
            summary={
                "total_decisions": len(decisions),
                "decisions_tested": len(tested),
                "decisions_with_bias": len(with_bias),
                "bias_rate": len(with_bias) / len(tested) if tested else 0.0,
                "avg_fairness_score": sum(d.fairness_score for d in tested if d.fairness_score) / len(tested) if tested else 0.0
            },
            bias_breakdown={
                "counts": dict(bias_counts),
                "most_common": max(bias_counts, key=bias_counts.get) if bias_counts else None,
                "total_instances": sum(bias_counts.values())
            },
            recommendations=recommendations,
            decision_type_analysis=dict(by_type)
        )

    def _generate_fairness_recommendations(
        self,
        tested: int,
        with_bias: int,
        bias_counts: Dict[str, int]
    ) -> List[str]:
        """Generate actionable fairness recommendations."""
        recommendations = []

        if tested == 0:
            recommendations.append("Enable counterfactual fairness testing for all decision types")
            return recommendations

        bias_rate = with_bias / tested

        if bias_rate > 0.2:
            recommendations.append(
                f"CRITICAL: High bias rate ({bias_rate:.1%}). Review decision criteria immediately."
            )

        if bias_rate > 0.1:
            recommendations.append(
                "Consider adding additional human review for flagged decisions"
            )

        if "name" in bias_counts and bias_counts["name"] > 0:
            recommendations.append(
                "Name-based bias detected. Consider anonymizing candidate names in initial screening."
            )

        if "location" in bias_counts and bias_counts["location"] > 0:
            recommendations.append(
                "Location bias detected. Review geographic criteria for discriminatory patterns."
            )

        if "gender" in bias_counts and bias_counts["gender"] > 0:
            recommendations.append(
                "Gender bias detected. Audit language patterns and gender-coded criteria."
            )

        if not recommendations:
            recommendations.append(
                "Fairness metrics within acceptable ranges. Continue monitoring."
            )

        return recommendations

    def get_reviewer_performance(
        self,
        window_days: int = 30
    ) -> List[ReviewerPerformance]:
        """
        Get reviewer performance metrics.

        Args:
            window_days: Time window in days

        Returns:
            List of ReviewerPerformance for each reviewer
        """
        if not self._metrics:
            return []

        now = datetime.now()
        start = now - timedelta(days=window_days)

        # Filter activity
        activity = [
            a for a in self._metrics._reviewer_activity
            if a.timestamp >= start
        ]

        # Aggregate by reviewer
        by_reviewer: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0, "agrees": 0, "overrides": 0, "escalations": 0
        })

        for a in activity:
            r = by_reviewer[a.reviewer_id]
            r["total"] += 1
            if a.action == "agree":
                r["agrees"] += 1
            elif a.is_override:
                r["overrides"] += 1
            elif a.action == "escalate":
                r["escalations"] += 1

        # Build performance objects
        performance = []
        for reviewer_id, stats in by_reviewer.items():
            total = stats["total"]
            performance.append(ReviewerPerformance(
                reviewer_id=reviewer_id,
                total_reviews=total,
                agreements=stats["agrees"],
                overrides=stats["overrides"],
                escalations=stats["escalations"],
                agreement_rate=stats["agrees"] / total if total > 0 else 0.0,
                override_rate=stats["overrides"] / total if total > 0 else 0.0
            ))

        # Sort by total reviews
        performance.sort(key=lambda x: x.total_reviews, reverse=True)

        return performance

    def generate_full_report(
        self,
        window_days: int = 7
    ) -> AnalyticsReport:
        """
        Generate comprehensive analytics report.

        Args:
            window_days: Time window in days

        Returns:
            Full AnalyticsReport
        """
        fairness = self.generate_fairness_report(window_days)
        trends = self.get_decision_trends(window_days)
        reviewers = self.get_reviewer_performance(window_days)

        # Calculate decision summary
        total_decisions = sum(t.total for t in trends)
        total_approved = sum(t.approved for t in trends)
        total_denied = sum(t.denied for t in trends)
        total_review = sum(t.needs_review for t in trends)

        # Identify alerts
        alerts = []
        if fairness.summary.get("bias_rate", 0) > 0.1:
            alerts.append({
                "type": "high_bias_rate",
                "severity": "warning",
                "message": f"Bias rate is {fairness.summary['bias_rate']:.1%}"
            })

        low_approval_days = [t for t in trends if t.approval_rate < 0.3 and t.total > 0]
        if low_approval_days:
            alerts.append({
                "type": "low_approval_rate",
                "severity": "info",
                "message": f"{len(low_approval_days)} days with low approval rate"
            })

        return AnalyticsReport(
            report_id=self._generate_report_id(),
            generated_at=datetime.now().isoformat(),
            period=f"Last {window_days} days",
            decision_summary={
                "total": total_decisions,
                "approved": total_approved,
                "denied": total_denied,
                "needs_review": total_review,
                "approval_rate": total_approved / total_decisions if total_decisions > 0 else 0.0
            },
            fairness_summary=fairness.summary,
            reviewer_summary={
                "total_reviewers": len(reviewers),
                "total_reviews": sum(r.total_reviews for r in reviewers),
                "avg_agreement_rate": sum(r.agreement_rate for r in reviewers) / len(reviewers) if reviewers else 0.0,
                "top_reviewers": [asdict(r) for r in reviewers[:5]]
            },
            trends=[asdict(t) for t in trends],
            alerts=alerts
        )

    def export_report(
        self,
        report: AnalyticsReport,
        format: ReportFormat = ReportFormat.JSON
    ) -> str:
        """
        Export report to specified format.

        Args:
            report: Report to export
            format: Output format (JSON or CSV)

        Returns:
            Formatted report string
        """
        if format == ReportFormat.JSON:
            return json.dumps(asdict(report), indent=2, default=str)

        elif format == ReportFormat.CSV:
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(["TrustChain Analytics Report"])
            writer.writerow(["Generated", report.generated_at])
            writer.writerow(["Period", report.period])
            writer.writerow([])

            # Decision Summary
            writer.writerow(["Decision Summary"])
            for key, value in report.decision_summary.items():
                writer.writerow([key, value])
            writer.writerow([])

            # Fairness Summary
            writer.writerow(["Fairness Summary"])
            for key, value in report.fairness_summary.items():
                writer.writerow([key, value])
            writer.writerow([])

            # Trends
            writer.writerow(["Daily Trends"])
            writer.writerow(["Date", "Total", "Approved", "Denied", "Review", "Approval Rate", "Avg Confidence"])
            for trend in report.trends:
                writer.writerow([
                    trend["date"],
                    trend["total"],
                    trend["approved"],
                    trend["denied"],
                    trend["needs_review"],
                    f"{trend['approval_rate']:.2%}",
                    f"{trend['avg_confidence']:.2%}"
                ])

            return output.getvalue()

        raise ValueError(f"Unsupported format: {format}")


# Global analytics service instance
analytics_service = AnalyticsService()
