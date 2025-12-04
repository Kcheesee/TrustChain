"""
TrustChain Services Module

Exports business logic services.

The TrustChain service is the new primary entry point for the
modular accountability framework. The DecisionOrchestrator is
kept for backward compatibility.

Built with care by Kareem & Claude
"""

from .orchestrator import DecisionOrchestrator
from .bias_detection import BiasDetectionService, get_bias_detector
from .trustchain import TrustChain
from .websocket_manager import ConnectionManager, manager, ChannelType
from .dashboard_metrics import DashboardMetrics, dashboard_metrics, TimeWindow, MetricsSummary
from .health import HealthService, health_service, HealthStatus
from .analytics import AnalyticsService, analytics_service, ReportFormat

__all__ = [
    # New modular service
    "TrustChain",
    # Phase 6: Real-time dashboard
    "ConnectionManager",
    "manager",
    "ChannelType",
    "DashboardMetrics",
    "dashboard_metrics",
    "TimeWindow",
    "MetricsSummary",
    # Phase 7: Production health
    "HealthService",
    "health_service",
    "HealthStatus",
    # Phase 9: Analytics
    "AnalyticsService",
    "analytics_service",
    "ReportFormat",
    # Legacy services (kept for backward compatibility)
    "DecisionOrchestrator",
    "BiasDetectionService",
    "get_bias_detector",
]
