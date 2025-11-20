"""
Tests for safety monitoring system.
"""

import pytest
from datetime import datetime, timedelta
from services.safety_monitor import (
    SafetyMonitor,
    ProviderHealthMonitor,
    AlertSeverity,
    get_safety_monitor,
    get_provider_health_monitor
)


class TestSafetyMonitor:
    """Test safety monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create safety monitor."""
        return SafetyMonitor(
            bias_rate_threshold=0.15,
            consensus_threshold=0.5,
            override_rate_threshold=0.3
        )
    
    def test_bias_rate_tracking(self, monitor):
        """Test bias detection rate tracking."""
        # Track 20 decisions with 10% bias
        for i in range(20):
            monitor.track_bias_detection(i < 2)  # 2 out of 20 = 10%
        
        metrics = monitor.get_metrics()
        assert metrics["bias_detection_rate"] == 0.1
        assert len(monitor.get_recent_alerts()) == 0  # Below threshold
    
    def test_high_bias_rate_alert(self, monitor):
        """Test alert when bias rate too high."""
        # Track 20 decisions with 20% bias (above 15% threshold)
        for i in range(20):
            monitor.track_bias_detection(i < 4)  # 4 out of 20 = 20%
        
        alerts = monitor.get_recent_alerts()
        assert len(alerts) > 0
        assert alerts[0].alert_type == "high_bias_rate"
        assert alerts[0].severity == AlertSeverity.CRITICAL
    
    def test_consensus_degradation(self, monitor):
        """Test consensus degradation detection."""
        # Track 20 decisions with low consensus
        for _ in range(20):
            monitor.track_consensus(0.4)  # Below 0.5 threshold
        
        alerts = monitor.get_recent_alerts()
        assert len(alerts) > 0
        assert alerts[0].alert_type == "consensus_degradation"
    
    def test_human_override_tracking(self, monitor):
        """Test human override rate tracking."""
        # Track 20 decisions with 40% overrides (above 30% threshold)
        for i in range(20):
            monitor.track_human_override(i < 8)  # 8 out of 20 = 40%
        
        alerts = monitor.get_recent_alerts()
        assert len(alerts) > 0
        assert alerts[0].alert_type == "high_override_rate"
    
    def test_metrics_calculation(self, monitor):
        """Test metrics calculation."""
        # Add some data
        for i in range(10):
            monitor.track_bias_detection(i < 2)
            monitor.track_consensus(0.8)
            monitor.track_human_override(i < 1)
        
        metrics = monitor.get_metrics()
        assert metrics["bias_detection_rate"] == 0.2
        assert metrics["average_consensus"] == 0.8
        assert metrics["human_override_rate"] == 0.1


class TestProviderHealthMonitor:
    """Test provider health monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create provider health monitor."""
        return ProviderHealthMonitor(
            error_threshold=0.5,
            min_requests=10,
            reset_timeout=60
        )
    
    def test_healthy_provider(self, monitor):
        """Test healthy provider tracking."""
        # Record 10 successful requests
        for _ in range(10):
            monitor.record_request("anthropic", success=True, latency_ms=100)
        
        assert monitor.is_healthy("anthropic")
        assert monitor.get_health_score("anthropic") == 1.0
    
    def test_circuit_breaker_opens(self, monitor):
        """Test circuit breaker opens on high error rate."""
        # Record 10 requests with 60% errors (above 50% threshold)
        for i in range(10):
            monitor.record_request("openai", success=i >= 6, latency_ms=100)
        
        assert not monitor.is_healthy("openai")
        assert monitor.get_health_score("openai") == 0.0
        
        health = monitor.get_all_health()
        assert health["openai"]["circuit_open"] is True
    
    def test_circuit_breaker_needs_min_requests(self, monitor):
        """Test circuit doesn't open without minimum requests."""
        # Record only 5 requests (below min_requests=10)
        for i in range(5):
            monitor.record_request("llama", success=False, latency_ms=100)
        
        # Circuit should not open yet
        assert monitor.is_healthy("llama")
    
    def test_health_metrics(self, monitor):
        """Test health metrics calculation."""
        # Record mixed results
        for i in range(20):
            monitor.record_request("anthropic", success=i < 15, latency_ms=100 + i*10)
        
        health = monitor.get_all_health()
        assert "anthropic" in health
        assert health["anthropic"]["total_requests"] == 20
        assert health["anthropic"]["error_count"] == 5
        assert health["anthropic"]["error_rate"] == 0.25
        assert health["anthropic"]["avg_latency_ms"] > 0


class TestMonitorSingletons:
    """Test singleton instances."""
    
    def test_safety_monitor_singleton(self):
        """Test safety monitor singleton."""
        monitor1 = get_safety_monitor()
        monitor2 = get_safety_monitor()
        assert monitor1 is monitor2
    
    def test_provider_health_monitor_singleton(self):
        """Test provider health monitor singleton."""
        monitor1 = get_provider_health_monitor()
        monitor2 = get_provider_health_monitor()
        assert monitor1 is monitor2
