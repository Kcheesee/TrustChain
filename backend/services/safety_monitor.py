"""
Safety Monitoring System for TrustChain.

Real-time monitoring of bias detection rates, consensus quality,
and system safety metrics with alerting capabilities.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SafetyAlert:
    """Safety alert notification."""
    alert_type: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime
    details: Dict[str, Any]


class SafetyMonitor:
    """
    Monitor system safety metrics and trigger alerts.
    
    Tracks:
    - Bias detection rate
    - Consensus degradation
    - Human override rate
    - Decision quality metrics
    """
    
    def __init__(
        self,
        bias_rate_threshold: float = 0.15,  # Alert if >15% bias detected
        consensus_threshold: float = 0.5,   # Alert if consensus <50%
        override_rate_threshold: float = 0.3  # Alert if >30% overrides
    ):
        """
        Initialize safety monitor.
        
        Args:
            bias_rate_threshold: Max acceptable bias detection rate
            consensus_threshold: Min acceptable consensus level
            override_rate_threshold: Max acceptable human override rate
        """
        self.bias_rate_threshold = bias_rate_threshold
        self.consensus_threshold = consensus_threshold
        self.override_rate_threshold = override_rate_threshold
        
        # Historical metrics
        self.bias_history: List[bool] = []
        self.consensus_history: List[float] = []
        self.override_history: List[bool] = []
        
        # Alert history
        self.alerts: List[SafetyAlert] = []
        
        logger.info("Safety monitor initialized")
    
    def track_bias_detection(self, bias_detected: bool):
        """
        Track bias detection event.
        
        Args:
            bias_detected: Whether bias was detected
        """
        self.bias_history.append(bias_detected)
        
        # Keep last 100 decisions
        if len(self.bias_history) > 100:
            self.bias_history.pop(0)
        
        # Check if rate is too high
        if len(self.bias_history) >= 20:  # Need minimum sample
            bias_rate = sum(self.bias_history) / len(self.bias_history)
            
            if bias_rate > self.bias_rate_threshold:
                alert = SafetyAlert(
                    alert_type="high_bias_rate",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Bias detection rate ({bias_rate:.1%}) exceeds threshold ({self.bias_rate_threshold:.1%})",
                    metric_value=bias_rate,
                    threshold=self.bias_rate_threshold,
                    timestamp=datetime.now(),
                    details={
                        "recent_decisions": len(self.bias_history),
                        "bias_detected_count": sum(self.bias_history)
                    }
                )
                self._trigger_alert(alert)
    
    def track_consensus(self, consensus_level: float):
        """
        Track consensus quality.
        
        Args:
            consensus_level: Consensus level (0-1)
        """
        self.consensus_history.append(consensus_level)
        
        # Keep last 100 decisions
        if len(self.consensus_history) > 100:
            self.consensus_history.pop(0)
        
        # Check for degradation
        if len(self.consensus_history) >= 20:
            avg_consensus = statistics.mean(self.consensus_history)
            
            if avg_consensus < self.consensus_threshold:
                alert = SafetyAlert(
                    alert_type="consensus_degradation",
                    severity=AlertSeverity.WARNING,
                    message=f"Average consensus ({avg_consensus:.1%}) below threshold ({self.consensus_threshold:.1%})",
                    metric_value=avg_consensus,
                    threshold=self.consensus_threshold,
                    timestamp=datetime.now(),
                    details={
                        "recent_decisions": len(self.consensus_history),
                        "min_consensus": min(self.consensus_history),
                        "max_consensus": max(self.consensus_history)
                    }
                )
                self._trigger_alert(alert)
    
    def track_human_override(self, was_overridden: bool):
        """
        Track human override events.
        
        Args:
            was_overridden: Whether human overrode AI decision
        """
        self.override_history.append(was_overridden)
        
        # Keep last 100 decisions
        if len(self.override_history) > 100:
            self.override_history.pop(0)
        
        # Check override rate
        if len(self.override_history) >= 20:
            override_rate = sum(self.override_history) / len(self.override_history)
            
            if override_rate > self.override_rate_threshold:
                alert = SafetyAlert(
                    alert_type="high_override_rate",
                    severity=AlertSeverity.WARNING,
                    message=f"Human override rate ({override_rate:.1%}) exceeds threshold ({self.override_rate_threshold:.1%})",
                    metric_value=override_rate,
                    threshold=self.override_rate_threshold,
                    timestamp=datetime.now(),
                    details={
                        "recent_decisions": len(self.override_history),
                        "override_count": sum(self.override_history),
                        "recommendation": "Review AI model performance and retrain if necessary"
                    }
                )
                self._trigger_alert(alert)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current safety metrics.
        
        Returns:
            Dictionary of current metrics
        """
        metrics = {
            "bias_detection_rate": sum(self.bias_history) / len(self.bias_history) if self.bias_history else 0,
            "average_consensus": statistics.mean(self.consensus_history) if self.consensus_history else 0,
            "human_override_rate": sum(self.override_history) / len(self.override_history) if self.override_history else 0,
            "sample_size": {
                "bias": len(self.bias_history),
                "consensus": len(self.consensus_history),
                "overrides": len(self.override_history)
            },
            "recent_alerts": len([a for a in self.alerts if a.timestamp > datetime.now() - timedelta(hours=24)])
        }
        
        return metrics
    
    def get_recent_alerts(self, hours: int = 24) -> List[SafetyAlert]:
        """
        Get recent alerts.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent alerts
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp > cutoff]
    
    def _trigger_alert(self, alert: SafetyAlert):
        """
        Trigger safety alert.
        
        Args:
            alert: Alert to trigger
        """
        self.alerts.append(alert)
        
        # Log alert
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(f"🚨 SAFETY ALERT: {alert.message}")
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(f"⚠️  SAFETY ALERT: {alert.message}")
        else:
            logger.info(f"ℹ️  SAFETY ALERT: {alert.message}")
        
        # In production, send to alerting system (PagerDuty, Slack, etc.)
        # self._send_to_alerting_system(alert)


class ProviderHealthMonitor:
    """
    Monitor AI provider health with circuit breaker pattern.
    
    Tracks provider performance and automatically routes around
    unhealthy providers.
    """
    
    def __init__(
        self,
        error_threshold: float = 0.5,  # Open circuit if >50% errors
        min_requests: int = 10,  # Minimum requests before opening circuit
        reset_timeout: int = 60  # Seconds before attempting reset
    ):
        """
        Initialize provider health monitor.
        
        Args:
            error_threshold: Error rate to open circuit breaker
            min_requests: Minimum requests before circuit can open
            reset_timeout: Seconds before trying to close circuit
        """
        self.error_threshold = error_threshold
        self.min_requests = min_requests
        self.reset_timeout = reset_timeout
        
        # Provider metrics
        self.provider_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Provider health monitor initialized")
    
    def record_request(self, provider: str, success: bool, latency_ms: float):
        """
        Record provider request.
        
        Args:
            provider: Provider name
            success: Whether request succeeded
            latency_ms: Request latency in milliseconds
        """
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {
                "total_requests": 0,
                "error_count": 0,
                "latencies": [],
                "circuit_open": False,
                "circuit_opened_at": None,
                "last_success_at": None
            }
        
        stats = self.provider_stats[provider]
        stats["total_requests"] += 1
        
        if not success:
            stats["error_count"] += 1
        else:
            stats["last_success_at"] = datetime.now()
        
        stats["latencies"].append(latency_ms)
        
        # Keep last 100 latencies
        if len(stats["latencies"]) > 100:
            stats["latencies"].pop(0)
        
        # Check if circuit should open
        self._check_circuit_breaker(provider)
    
    def is_healthy(self, provider: str) -> bool:
        """
        Check if provider is healthy.
        
        Args:
            provider: Provider name
            
        Returns:
            True if provider is healthy
        """
        if provider not in self.provider_stats:
            return True  # Unknown providers assumed healthy
        
        stats = self.provider_stats[provider]
        
        # Check circuit breaker
        if stats["circuit_open"]:
            # Try to reset if timeout passed
            if stats["circuit_opened_at"]:
                elapsed = (datetime.now() - stats["circuit_opened_at"]).total_seconds()
                if elapsed > self.reset_timeout:
                    logger.info(f"Attempting to reset circuit for {provider}")
                    stats["circuit_open"] = False
                    stats["circuit_opened_at"] = None
                    return True
            return False
        
        return True
    
    def get_health_score(self, provider: str) -> float:
        """
        Get provider health score (0-1).
        
        Args:
            provider: Provider name
            
        Returns:
            Health score (1 = perfect, 0 = completely unhealthy)
        """
        if provider not in self.provider_stats:
            return 1.0
        
        stats = self.provider_stats[provider]
        
        if stats["circuit_open"]:
            return 0.0
        
        if stats["total_requests"] == 0:
            return 1.0
        
        # Calculate error rate
        error_rate = stats["error_count"] / stats["total_requests"]
        success_rate = 1.0 - error_rate
        
        return success_rate
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all providers.
        
        Returns:
            Dictionary of provider health metrics
        """
        health = {}
        
        for provider, stats in self.provider_stats.items():
            health[provider] = {
                "is_healthy": self.is_healthy(provider),
                "health_score": self.get_health_score(provider),
                "total_requests": stats["total_requests"],
                "error_count": stats["error_count"],
                "error_rate": stats["error_count"] / stats["total_requests"] if stats["total_requests"] > 0 else 0,
                "avg_latency_ms": statistics.mean(stats["latencies"]) if stats["latencies"] else 0,
                "circuit_open": stats["circuit_open"],
                "last_success_at": stats["last_success_at"].isoformat() if stats["last_success_at"] else None
            }
        
        return health
    
    def _check_circuit_breaker(self, provider: str):
        """
        Check if circuit breaker should open.
        
        Args:
            provider: Provider name
        """
        stats = self.provider_stats[provider]
        
        # Need minimum requests
        if stats["total_requests"] < self.min_requests:
            return
        
        # Calculate error rate
        error_rate = stats["error_count"] / stats["total_requests"]
        
        # Open circuit if error rate too high
        if error_rate > self.error_threshold and not stats["circuit_open"]:
            stats["circuit_open"] = True
            stats["circuit_opened_at"] = datetime.now()
            
            logger.critical(
                f"🚨 Circuit breaker OPENED for {provider}: "
                f"error rate {error_rate:.1%} exceeds threshold {self.error_threshold:.1%}"
            )


# Global instances
_safety_monitor: Optional[SafetyMonitor] = None
_provider_health_monitor: Optional[ProviderHealthMonitor] = None


def get_safety_monitor() -> SafetyMonitor:
    """Get global safety monitor instance."""
    global _safety_monitor
    if _safety_monitor is None:
        _safety_monitor = SafetyMonitor()
    return _safety_monitor


def get_provider_health_monitor() -> ProviderHealthMonitor:
    """Get global provider health monitor instance."""
    global _provider_health_monitor
    if _provider_health_monitor is None:
        _provider_health_monitor = ProviderHealthMonitor()
    return _provider_health_monitor
