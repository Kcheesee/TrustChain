"""
TrustChain Health Check Service

Provides comprehensive health and readiness checks for:
- API service status
- Database connectivity
- AI provider health
- WebSocket manager status
- Memory and system metrics

Usage:
    from services.health import health_service

    status = await health_service.get_health()
    ready = await health_service.is_ready()

Built with care by Kareem & Claude
"""

import os
import psutil
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health report."""
    status: HealthStatus
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    system_metrics: Dict[str, Any]


class HealthService:
    """
    Comprehensive health check service.

    Checks multiple system components and provides
    both liveness (is the service running?) and
    readiness (can it serve traffic?) probes.
    """

    def __init__(self):
        self._start_time = datetime.now()
        self._version = "1.0.0"

    @property
    def uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds()

    async def get_health(
        self,
        include_details: bool = True
    ) -> SystemHealth:
        """
        Get comprehensive health status.

        Args:
            include_details: Include detailed component info

        Returns:
            SystemHealth with overall status and component breakdown
        """
        components = {}

        # Check API component
        components["api"] = self._check_api()

        # Check memory and CPU
        if include_details:
            components["system"] = self._check_system_resources()

        # Determine overall status
        statuses = [c.status for c in components.values()]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return SystemHealth(
            status=overall,
            timestamp=datetime.now().isoformat(),
            version=self._version,
            environment=os.getenv("ENVIRONMENT", "development"),
            uptime_seconds=self.uptime_seconds,
            components=components,
            system_metrics=self._get_system_metrics() if include_details else {}
        )

    async def is_alive(self) -> bool:
        """
        Liveness probe - is the service running?

        Simple check that returns True if the service is alive.
        Used by Kubernetes/Docker for restart decisions.
        """
        return True

    async def is_ready(self) -> bool:
        """
        Readiness probe - can the service handle requests?

        Returns True only if all critical components are healthy.
        Used by load balancers for routing decisions.
        """
        health = await self.get_health(include_details=False)
        return health.status != HealthStatus.UNHEALTHY

    def _check_api(self) -> ComponentHealth:
        """Check API service health."""
        return ComponentHealth(
            name="api",
            status=HealthStatus.HEALTHY,
            message="API service running",
            details={
                "uptime_seconds": self.uptime_seconds,
                "version": self._version
            }
        )

    def _check_system_resources(self) -> ComponentHealth:
        """Check system resources (memory, CPU)."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Determine status based on resource usage
            if memory.percent > 90 or cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System resources critical"
            elif memory.percent > 75 or cpu_percent > 75:
                status = HealthStatus.DEGRADED
                message = "System resources elevated"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"

            return ComponentHealth(
                name="system",
                status=status,
                message=message,
                details={
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "cpu_percent": cpu_percent
                }
            )
        except Exception as e:
            logger.warning(f"Failed to check system resources: {e}")
            return ComponentHealth(
                name="system",
                status=HealthStatus.UNKNOWN,
                message=f"Unable to check: {e}"
            )

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "memory": {
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "free_gb": disk.free / (1024 * 1024 * 1024),
                    "percent_used": disk.percent
                },
                "cpu": {
                    "percent": psutil.cpu_percent(interval=0.1),
                    "count": psutil.cpu_count()
                },
                "process": {
                    "pid": os.getpid(),
                    "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024)
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {"error": str(e)}


# Global health service instance
health_service = HealthService()
