"""
TrustChain Phase 9: Analytics and Reporting Tests

Tests for analytics service and reporting endpoints.

Built with care by Kareem & Claude
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from services.analytics import (
    AnalyticsService,
    analytics_service,
    ReportFormat,
    DecisionTrend,
    FairnessReport,
    ReviewerPerformance,
    AnalyticsReport,
)
from services.dashboard_metrics import DashboardMetrics, DecisionMetric, ReviewerMetric


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def metrics_with_data():
    """Create DashboardMetrics with test data."""
    metrics = DashboardMetrics()

    # Add decisions over several days
    now = datetime.now()

    for i in range(30):
        day_offset = i % 7
        decision = DecisionMetric(
            result_id=f"tc_{i}",
            case_id=f"case_{i}",
            decision_type="hiring" if i % 2 == 0 else "benefits",
            final_decision=["approved", "denied", "needs_review"][i % 3],
            confidence=0.7 + (i % 3) * 0.1,
            requires_review=i % 3 == 2,
            fairness_score=0.9 - (i % 10) * 0.05 if i % 2 == 0 else None,
            biases_detected=["name"] if i % 5 == 0 else [],
            timestamp=now - timedelta(days=day_offset, hours=i)
        )
        metrics._decisions.append(decision)

    # Add reviewer activity
    for i in range(20):
        activity = ReviewerMetric(
            reviewer_id=f"reviewer_{i % 3}",
            action="agree" if i % 3 != 0 else "override_approve",
            result_id=f"tc_{i}",
            timestamp=now - timedelta(days=i % 7),
            is_override=i % 3 == 0
        )
        metrics._reviewer_activity.append(activity)

    return metrics


# ============================================================================
# AnalyticsService Tests
# ============================================================================

class TestAnalyticsService:
    """Test AnalyticsService functionality."""

    def test_init(self):
        """Test service initialization."""
        service = AnalyticsService()
        assert service._metrics is None
        assert service._report_counter == 0

    def test_set_metrics_source(self, metrics_with_data):
        """Test setting metrics source."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)
        assert service._metrics is metrics_with_data

    def test_generate_report_id(self):
        """Test report ID generation."""
        service = AnalyticsService()
        id1 = service._generate_report_id()
        id2 = service._generate_report_id()

        assert id1.startswith("rpt_")
        assert id2.startswith("rpt_")
        assert id1 != id2


class TestDecisionTrends:
    """Test decision trend analysis."""

    def test_get_trends_empty(self):
        """Test trends with no data."""
        service = AnalyticsService()
        trends = service.get_decision_trends(days=7)
        assert trends == []

    def test_get_trends_with_data(self, metrics_with_data):
        """Test trends with data."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        trends = service.get_decision_trends(days=7)

        assert len(trends) == 7
        for trend in trends:
            assert isinstance(trend, DecisionTrend)
            assert hasattr(trend, "date")
            assert hasattr(trend, "total")
            assert hasattr(trend, "approval_rate")

    def test_get_trends_filtered(self, metrics_with_data):
        """Test trends filtered by decision type."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        trends = service.get_decision_trends(days=7, decision_type="hiring")

        assert len(trends) == 7
        # Filtered trends should have fewer or equal decisions
        total_hiring = sum(t.total for t in trends)
        all_trends = service.get_decision_trends(days=7)
        total_all = sum(t.total for t in all_trends)
        assert total_hiring <= total_all


class TestFairnessReport:
    """Test fairness report generation."""

    def test_generate_report_empty(self):
        """Test report with no data."""
        service = AnalyticsService()
        service.set_metrics_source(DashboardMetrics())

        report = service.generate_fairness_report(window_days=1)

        assert isinstance(report, FairnessReport)
        assert report.summary["total_decisions"] == 0

    def test_generate_report_with_data(self, metrics_with_data):
        """Test report with data."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        report = service.generate_fairness_report(window_days=7)

        assert isinstance(report, FairnessReport)
        assert report.report_id.startswith("rpt_")
        assert "total_decisions" in report.summary
        assert "bias_rate" in report.summary
        assert isinstance(report.recommendations, list)

    def test_report_has_recommendations(self, metrics_with_data):
        """Test that reports include recommendations."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        report = service.generate_fairness_report(window_days=7)

        assert len(report.recommendations) > 0


class TestReviewerPerformance:
    """Test reviewer performance metrics."""

    def test_get_performance_empty(self):
        """Test performance with no data."""
        service = AnalyticsService()
        service.set_metrics_source(DashboardMetrics())

        performance = service.get_reviewer_performance(window_days=30)

        assert performance == []

    def test_get_performance_with_data(self, metrics_with_data):
        """Test performance with data."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        performance = service.get_reviewer_performance(window_days=30)

        assert len(performance) > 0
        for p in performance:
            assert isinstance(p, ReviewerPerformance)
            assert p.total_reviews > 0
            assert 0 <= p.agreement_rate <= 1
            assert 0 <= p.override_rate <= 1


class TestFullReport:
    """Test full analytics report."""

    def test_generate_full_report(self, metrics_with_data):
        """Test full report generation."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        report = service.generate_full_report(window_days=7)

        assert isinstance(report, AnalyticsReport)
        assert "total" in report.decision_summary
        assert len(report.trends) == 7
        assert isinstance(report.alerts, list)


class TestExport:
    """Test report export functionality."""

    def test_export_json(self, metrics_with_data):
        """Test JSON export."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        report = service.generate_full_report(window_days=7)
        exported = service.export_report(report, ReportFormat.JSON)

        assert isinstance(exported, str)
        import json
        parsed = json.loads(exported)
        assert "report_id" in parsed

    def test_export_csv(self, metrics_with_data):
        """Test CSV export."""
        service = AnalyticsService()
        service.set_metrics_source(metrics_with_data)

        report = service.generate_full_report(window_days=7)
        exported = service.export_report(report, ReportFormat.CSV)

        assert isinstance(exported, str)
        assert "TrustChain Analytics Report" in exported
        assert "Decision Summary" in exported
        assert "Daily Trends" in exported


class TestReportFormat:
    """Test ReportFormat enum."""

    def test_format_values(self):
        """Test format enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.CSV.value == "csv"


class TestGlobalInstance:
    """Test global analytics service instance."""

    def test_global_instance_exists(self):
        """Test that global instance is available."""
        assert analytics_service is not None
        assert isinstance(analytics_service, AnalyticsService)
