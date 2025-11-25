"""
TrustChain Phase 6: Real-time Dashboard Tests

Tests for WebSocket manager, dashboard metrics, and API endpoints.

Built with care by Kareem & Claude
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.websocket_manager import (
    ConnectionManager,
    WebSocketConnection,
    ChannelType,
)
from services.dashboard_metrics import (
    DashboardMetrics,
    DecisionMetric,
    ReviewerMetric,
    MetricsSummary,
    TimeWindow,
)


# ============================================================================
# ConnectionManager Tests
# ============================================================================

class TestConnectionManager:
    """Test WebSocket ConnectionManager."""

    def test_init(self):
        """Test manager initialization."""
        manager = ConnectionManager()

        assert len(manager._channels) == len(ChannelType)
        assert len(manager._connections) == 0
        assert manager._total_messages_sent == 0

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test WebSocket connection."""
        manager = ConnectionManager()

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        connection = await manager.connect(
            mock_ws,
            channels=["decisions", "alerts"],
            client_id="test_client"
        )

        assert connection.client_id == "test_client"
        assert "decisions" in connection.channels
        assert "alerts" in connection.channels
        assert mock_ws in manager._connections
        assert mock_ws.accept.called
        assert mock_ws.send_json.called

    def test_disconnect(self):
        """Test WebSocket disconnection."""
        manager = ConnectionManager()

        # Add a mock connection manually
        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            channels={"decisions", "alerts"},
            client_id="test_client"
        )
        manager._connections[mock_ws] = connection
        manager._channels["decisions"].add(mock_ws)
        manager._channels["alerts"].add(mock_ws)

        # Disconnect
        manager.disconnect(mock_ws, reason="test")

        assert mock_ws not in manager._connections
        assert mock_ws not in manager._channels["decisions"]
        assert mock_ws not in manager._channels["alerts"]

    def test_get_stats(self):
        """Test stats retrieval."""
        manager = ConnectionManager()

        stats = manager.get_stats()

        assert "active_connections" in stats
        assert "total_connections_ever" in stats
        assert "total_messages_sent" in stats
        assert "channels" in stats
        assert stats["active_connections"] == 0


class TestChannelType:
    """Test ChannelType enum."""

    def test_channel_values(self):
        """Test all channel types exist."""
        assert ChannelType.DECISIONS.value == "decisions"
        assert ChannelType.METRICS.value == "metrics"
        assert ChannelType.ALERTS.value == "alerts"
        assert ChannelType.REVIEWER_ACTIVITY.value == "reviewers"
        assert ChannelType.FAIRNESS.value == "fairness"
        assert ChannelType.ALL.value == "all"


# ============================================================================
# DashboardMetrics Tests
# ============================================================================

class TestDashboardMetrics:
    """Test DashboardMetrics service."""

    def test_init(self):
        """Test metrics initialization."""
        metrics = DashboardMetrics(max_history_hours=24)

        assert metrics.max_history == timedelta(hours=24)
        assert len(metrics._decisions) == 0
        assert len(metrics._reviewer_activity) == 0

    def test_record_decision(self):
        """Test recording a decision."""
        metrics = DashboardMetrics()

        result = {
            "result_id": "tc_123",
            "case_id": "case_456",
            "decision_type": "hiring",
            "final_decision": "approved",
            "overall_confidence": 0.85,
            "requires_human_review": False,
            "analysis_results": []
        }

        metrics.record_decision(result)

        assert len(metrics._decisions) == 1
        assert metrics._decisions[0].result_id == "tc_123"
        assert metrics._decisions[0].decision_type == "hiring"
        assert metrics._decisions[0].final_decision == "approved"

    def test_record_decision_with_fairness(self):
        """Test recording decision with fairness data."""
        metrics = DashboardMetrics()

        result = {
            "result_id": "tc_123",
            "case_id": "case_456",
            "decision_type": "hiring",
            "final_decision": "needs_review",
            "overall_confidence": 0.65,
            "requires_human_review": True,
            "analysis_results": [
                {
                    "analyzer_name": "counterfactual_fairness",
                    "details": {
                        "fairness_score": 0.45,
                        "biases_detected": ["name", "location"]
                    }
                }
            ]
        }

        metrics.record_decision(result)

        assert metrics._decisions[0].fairness_score == 0.45
        assert "name" in metrics._decisions[0].biases_detected
        assert "location" in metrics._decisions[0].biases_detected

    def test_record_reviewer_activity(self):
        """Test recording reviewer activity."""
        metrics = DashboardMetrics()

        metrics.record_reviewer_activity(
            reviewer_id="jane_hr",
            action="override_approve",
            result_id="tc_123",
            is_override=True
        )

        assert len(metrics._reviewer_activity) == 1
        assert metrics._reviewer_activity[0].reviewer_id == "jane_hr"
        assert metrics._reviewer_activity[0].is_override is True


class TestMetricsSummary:
    """Test metrics summary calculations."""

    def test_get_summary_empty(self):
        """Test summary with no data."""
        metrics = DashboardMetrics()

        summary = metrics.get_summary(window=TimeWindow.HOUR)

        assert summary.total_decisions == 0
        assert summary.approval_rate == 0.0

    def test_get_summary_with_data(self):
        """Test summary with decisions."""
        metrics = DashboardMetrics()

        # Add test decisions
        for i in range(10):
            decision = "approved" if i < 7 else "denied"
            metrics.record_decision({
                "result_id": f"tc_{i}",
                "case_id": f"case_{i}",
                "decision_type": "hiring",
                "final_decision": decision,
                "overall_confidence": 0.8 + (i * 0.01),
                "requires_human_review": False,
                "analysis_results": []
            })

        summary = metrics.get_summary(window=TimeWindow.HOUR)

        assert summary.total_decisions == 10
        assert summary.decisions_approved == 7
        assert summary.decisions_denied == 3
        assert summary.approval_rate == 0.7

    def test_get_summary_filtered_by_type(self):
        """Test summary filtered by decision type."""
        metrics = DashboardMetrics()

        # Add hiring decisions
        for i in range(5):
            metrics.record_decision({
                "result_id": f"tc_h{i}",
                "case_id": f"case_h{i}",
                "decision_type": "hiring",
                "final_decision": "approved",
                "overall_confidence": 0.85,
                "requires_human_review": False,
                "analysis_results": []
            })

        # Add benefits decisions
        for i in range(3):
            metrics.record_decision({
                "result_id": f"tc_b{i}",
                "case_id": f"case_b{i}",
                "decision_type": "benefits",
                "final_decision": "denied",
                "overall_confidence": 0.75,
                "requires_human_review": False,
                "analysis_results": []
            })

        # Get hiring only
        summary = metrics.get_summary(
            window=TimeWindow.HOUR,
            decision_type="hiring"
        )

        assert summary.total_decisions == 5
        assert summary.decisions_approved == 5


class TestTimeSeries:
    """Test time series data generation."""

    def test_get_time_series_empty(self):
        """Test time series with no data."""
        metrics = DashboardMetrics()

        series = metrics.get_time_series(
            metric_type="decisions",
            window=TimeWindow.HOUR,
            granularity_minutes=5
        )

        # Should have buckets even with no data
        assert isinstance(series, list)
        assert len(series) > 0

    def test_get_time_series_decisions(self):
        """Test decision time series."""
        metrics = DashboardMetrics()

        # Add some decisions
        for i in range(5):
            metrics.record_decision({
                "result_id": f"tc_{i}",
                "case_id": f"case_{i}",
                "decision_type": "hiring",
                "final_decision": "approved" if i % 2 == 0 else "denied",
                "overall_confidence": 0.8,
                "requires_human_review": False,
                "analysis_results": []
            })

        series = metrics.get_time_series(
            metric_type="decisions",
            window=TimeWindow.HOUR,
            granularity_minutes=5
        )

        assert isinstance(series, list)
        # Check structure
        for point in series:
            assert "timestamp" in point
            assert "total" in point
            assert "approved" in point
            assert "denied" in point

    def test_get_time_series_fairness(self):
        """Test fairness time series."""
        metrics = DashboardMetrics()

        # Add decisions with fairness scores
        for i in range(3):
            metrics.record_decision({
                "result_id": f"tc_{i}",
                "case_id": f"case_{i}",
                "decision_type": "hiring",
                "final_decision": "needs_review",
                "overall_confidence": 0.7,
                "requires_human_review": True,
                "analysis_results": [
                    {
                        "analyzer_name": "counterfactual_fairness",
                        "details": {
                            "fairness_score": 0.5 + (i * 0.1),
                            "biases_detected": []
                        }
                    }
                ]
            })

        series = metrics.get_time_series(
            metric_type="fairness",
            window=TimeWindow.HOUR,
            granularity_minutes=5
        )

        assert isinstance(series, list)


class TestReviewerSummary:
    """Test reviewer activity summary."""

    def test_get_reviewer_summary_empty(self):
        """Test reviewer summary with no data."""
        metrics = DashboardMetrics()

        summary = metrics.get_reviewer_summary(window=TimeWindow.DAY)

        assert summary["total_activity"] == 0
        assert summary["unique_reviewers"] == 0

    def test_get_reviewer_summary_with_data(self):
        """Test reviewer summary with activity."""
        metrics = DashboardMetrics()

        # Add reviewer activity
        metrics.record_reviewer_activity("jane_hr", "agree", "tc_1", False)
        metrics.record_reviewer_activity("jane_hr", "override_approve", "tc_2", True)
        metrics.record_reviewer_activity("bob_hr", "agree", "tc_3", False)
        metrics.record_reviewer_activity("bob_hr", "escalate", "tc_4", False)

        summary = metrics.get_reviewer_summary(window=TimeWindow.DAY)

        assert summary["total_activity"] == 4
        assert summary["unique_reviewers"] == 2
        assert summary["total_overrides"] == 1


class TestBiasBreakdown:
    """Test bias detection breakdown."""

    def test_get_bias_breakdown_empty(self):
        """Test bias breakdown with no data."""
        metrics = DashboardMetrics()

        breakdown = metrics.get_bias_breakdown(window=TimeWindow.DAY)

        assert breakdown["decisions_tested"] == 0
        assert breakdown["decisions_with_bias"] == 0

    def test_get_bias_breakdown_with_data(self):
        """Test bias breakdown with counterfactual results."""
        metrics = DashboardMetrics()

        # Add decisions with fairness testing
        metrics.record_decision({
            "result_id": "tc_1",
            "case_id": "case_1",
            "decision_type": "hiring",
            "final_decision": "needs_review",
            "overall_confidence": 0.6,
            "requires_human_review": True,
            "analysis_results": [
                {
                    "analyzer_name": "counterfactual_fairness",
                    "details": {
                        "fairness_score": 0.4,
                        "biases_detected": ["name", "location"]
                    }
                }
            ]
        })

        metrics.record_decision({
            "result_id": "tc_2",
            "case_id": "case_2",
            "decision_type": "hiring",
            "final_decision": "approved",
            "overall_confidence": 0.9,
            "requires_human_review": False,
            "analysis_results": [
                {
                    "analyzer_name": "counterfactual_fairness",
                    "details": {
                        "fairness_score": 0.95,
                        "biases_detected": []
                    }
                }
            ]
        })

        breakdown = metrics.get_bias_breakdown(window=TimeWindow.DAY)

        assert breakdown["decisions_tested"] == 2
        assert breakdown["decisions_with_bias"] == 1
        assert breakdown["bias_detection_rate"] == 0.5
        assert "name" in breakdown["bias_counts"]
        assert "location" in breakdown["bias_counts"]


class TestTimeWindow:
    """Test TimeWindow enum."""

    def test_time_window_values(self):
        """Test all time window values."""
        assert TimeWindow.MINUTE.value == "minute"
        assert TimeWindow.HOUR.value == "hour"
        assert TimeWindow.DAY.value == "day"
        assert TimeWindow.WEEK.value == "week"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for dashboard components."""

    def test_full_workflow(self):
        """Test complete metrics workflow."""
        metrics = DashboardMetrics()

        # Simulate a series of decisions
        for i in range(20):
            has_bias = i % 5 == 0  # 20% have bias

            metrics.record_decision({
                "result_id": f"tc_{i}",
                "case_id": f"case_{i}",
                "decision_type": "hiring" if i % 2 == 0 else "benefits",
                "final_decision": ["approved", "denied", "needs_review"][i % 3],
                "overall_confidence": 0.7 + (i % 3) * 0.1,
                "requires_human_review": i % 3 == 2,
                "analysis_results": [
                    {
                        "analyzer_name": "counterfactual_fairness",
                        "details": {
                            "fairness_score": 0.4 if has_bias else 0.9,
                            "biases_detected": ["name"] if has_bias else []
                        }
                    }
                ] if i % 2 == 0 else []  # Only hiring has fairness testing
            })

        # Simulate reviewer activity
        for i in range(10):
            metrics.record_reviewer_activity(
                reviewer_id=f"reviewer_{i % 3}",
                action="override_approve" if i % 4 == 0 else "agree",
                result_id=f"tc_{i}",
                is_override=i % 4 == 0
            )

        # Get all summaries
        summary = metrics.get_summary(window=TimeWindow.HOUR)
        time_series = metrics.get_time_series("decisions", TimeWindow.HOUR, 5)
        reviewer_summary = metrics.get_reviewer_summary(TimeWindow.DAY)
        bias_breakdown = metrics.get_bias_breakdown(TimeWindow.DAY)

        # Verify data
        assert summary.total_decisions == 20
        assert len(time_series) > 0
        assert reviewer_summary["total_activity"] == 10
        assert bias_breakdown["decisions_tested"] == 10  # Only hiring decisions

    @pytest.mark.asyncio
    async def test_websocket_broadcast_decision(self):
        """Test broadcasting decision to WebSocket clients."""
        manager = ConnectionManager()

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await manager.connect(mock_ws, channels=["decisions"])

        # Broadcast a decision
        sent = await manager.broadcast_decision({
            "result_id": "tc_123",
            "case_id": "case_456",
            "decision_type": "hiring",
            "final_decision": "approved",
            "overall_confidence": 0.85,
            "requires_human_review": False
        })

        assert sent == 1
        # Verify send_json was called (welcome message + broadcast)
        assert mock_ws.send_json.call_count >= 2
