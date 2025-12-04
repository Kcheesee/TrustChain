"""
TrustChain Phase 7: Production Health & Monitoring Tests

Tests for health check service and production readiness.

Built with care by Kareem & Claude
"""

import pytest
from services.health import (
    HealthService,
    health_service,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
)


# ============================================================================
# HealthService Tests
# ============================================================================

class TestHealthService:
    """Test HealthService functionality."""

    def test_init(self):
        """Test health service initialization."""
        service = HealthService()
        assert service._version == "1.0.0"
        assert service.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_is_alive(self):
        """Test liveness probe."""
        service = HealthService()
        is_alive = await service.is_alive()
        assert is_alive is True

    @pytest.mark.asyncio
    async def test_is_ready(self):
        """Test readiness probe."""
        service = HealthService()
        is_ready = await service.is_ready()
        assert isinstance(is_ready, bool)

    @pytest.mark.asyncio
    async def test_get_health(self):
        """Test comprehensive health check."""
        service = HealthService()
        health = await service.get_health(include_details=True)

        assert isinstance(health, SystemHealth)
        assert health.status in HealthStatus
        assert health.version == "1.0.0"
        assert "api" in health.components
        assert "system" in health.components
        assert health.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_get_health_without_details(self):
        """Test health check without detailed metrics."""
        service = HealthService()
        health = await service.get_health(include_details=False)

        assert isinstance(health, SystemHealth)
        assert health.status in HealthStatus
        # Should not include system metrics
        assert health.system_metrics == {}

    def test_check_api(self):
        """Test API component health check."""
        service = HealthService()
        api_health = service._check_api()

        assert isinstance(api_health, ComponentHealth)
        assert api_health.name == "api"
        assert api_health.status == HealthStatus.HEALTHY

    def test_check_system_resources(self):
        """Test system resources health check."""
        service = HealthService()
        sys_health = service._check_system_resources()

        assert isinstance(sys_health, ComponentHealth)
        assert sys_health.name == "system"
        assert sys_health.status in HealthStatus
        assert "memory_percent" in sys_health.details
        assert "cpu_percent" in sys_health.details

    def test_get_system_metrics(self):
        """Test system metrics retrieval."""
        service = HealthService()
        metrics = service._get_system_metrics()

        assert "memory" in metrics
        assert "disk" in metrics
        assert "cpu" in metrics
        assert "process" in metrics

        assert "total_mb" in metrics["memory"]
        assert "percent_used" in metrics["memory"]
        assert "free_gb" in metrics["disk"]
        assert "count" in metrics["cpu"]
        assert "pid" in metrics["process"]


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestComponentHealth:
    """Test ComponentHealth dataclass."""

    def test_component_health_creation(self):
        """Test ComponentHealth creation."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="Test message",
            latency_ms=10.5,
            details={"key": "value"}
        )

        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Test message"
        assert health.latency_ms == 10.5
        assert health.details == {"key": "value"}

    def test_component_health_defaults(self):
        """Test ComponentHealth defaults."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY
        )

        assert health.message == ""
        assert health.latency_ms is None
        assert health.details == {}


class TestGlobalInstance:
    """Test global health service instance."""

    @pytest.mark.asyncio
    async def test_global_instance_works(self):
        """Test that global instance is functional."""
        assert health_service is not None
        health = await health_service.get_health()
        assert health.status in HealthStatus
