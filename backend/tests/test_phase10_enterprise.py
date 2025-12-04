"""
TrustChain Phase 10: Enterprise Security Tests

Tests for API key authentication and rate limiting.

Built with care by Kareem & Claude
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock

from middleware.auth import (
    APIKeyAuth,
    api_key_auth,
    Scope,
    APIKeyInfo,
    APIKeyRecord,
)
from middleware.rate_limit import (
    RateLimiter,
    rate_limiter,
    RateLimitConfig,
    RateLimitExceeded,
    TokenBucket,
)


# ============================================================================
# API Key Authentication Tests
# ============================================================================

class TestAPIKeyAuth:
    """Test API key authentication."""

    def test_init(self):
        """Test auth manager initialization."""
        auth = APIKeyAuth()
        assert auth._keys is not None
        assert auth._key_counter == 0

    def test_generate_key(self):
        """Test key generation."""
        auth = APIKeyAuth()
        raw_key, key_info = auth.generate_key(
            client_name="Test Client",
            scopes=[Scope.READ, Scope.WRITE]
        )

        assert raw_key.startswith("tc_")
        assert key_info.client_name == "Test Client"
        assert Scope.READ in key_info.scopes
        assert Scope.WRITE in key_info.scopes

    def test_validate_key_valid(self):
        """Test validating a valid key."""
        auth = APIKeyAuth()
        raw_key, _ = auth.generate_key(
            client_name="Valid Client",
            scopes=[Scope.READ]
        )

        key_info = auth.validate_key(raw_key)

        assert key_info is not None
        assert key_info.client_name == "Valid Client"

    def test_validate_key_invalid(self):
        """Test validating an invalid key."""
        auth = APIKeyAuth()
        key_info = auth.validate_key("invalid_key")

        assert key_info is None

    def test_validate_key_empty(self):
        """Test validating empty key."""
        auth = APIKeyAuth()
        key_info = auth.validate_key("")

        assert key_info is None

    def test_revoke_key(self):
        """Test key revocation."""
        auth = APIKeyAuth()
        raw_key, key_info = auth.generate_key(
            client_name="Revoke Test",
            scopes=[Scope.READ]
        )

        # Key should work initially
        assert auth.validate_key(raw_key) is not None

        # Revoke the key
        assert auth.revoke_key(key_info.key_id) is True

        # Key should no longer work
        assert auth.validate_key(raw_key) is None

    def test_revoke_nonexistent_key(self):
        """Test revoking nonexistent key."""
        auth = APIKeyAuth()
        result = auth.revoke_key("nonexistent_key")
        assert result is False

    def test_check_scope_admin(self):
        """Test that admin scope grants all permissions."""
        auth = APIKeyAuth()
        _, key_info = auth.generate_key(
            client_name="Admin",
            scopes=[Scope.ADMIN]
        )

        assert auth.check_scope(key_info, [Scope.READ]) is True
        assert auth.check_scope(key_info, [Scope.WRITE]) is True
        assert auth.check_scope(key_info, [Scope.ANALYTICS]) is True

    def test_check_scope_limited(self):
        """Test limited scope checking."""
        auth = APIKeyAuth()
        _, key_info = auth.generate_key(
            client_name="Limited",
            scopes=[Scope.READ]
        )

        assert auth.check_scope(key_info, [Scope.READ]) is True
        assert auth.check_scope(key_info, [Scope.WRITE]) is False
        assert auth.check_scope(key_info, [Scope.READ, Scope.WRITE]) is False

    def test_list_keys(self):
        """Test listing all keys."""
        auth = APIKeyAuth()
        auth.generate_key("Client 1", [Scope.READ])
        auth.generate_key("Client 2", [Scope.WRITE])

        keys = auth.list_keys()

        assert len(keys) == 2
        client_names = {k.client_name for k in keys}
        assert "Client 1" in client_names
        assert "Client 2" in client_names

    def test_get_key_info(self):
        """Test getting key info by ID."""
        auth = APIKeyAuth()
        _, created_info = auth.generate_key("Test", [Scope.READ])

        retrieved_info = auth.get_key_info(created_info.key_id)

        assert retrieved_info is not None
        assert retrieved_info.key_id == created_info.key_id

    def test_get_key_info_nonexistent(self):
        """Test getting nonexistent key info."""
        auth = APIKeyAuth()
        info = auth.get_key_info("nonexistent")
        assert info is None


class TestScope:
    """Test Scope enum."""

    def test_scope_values(self):
        """Test scope enum values."""
        assert Scope.READ.value == "read"
        assert Scope.WRITE.value == "write"
        assert Scope.ANALYTICS.value == "analytics"
        assert Scope.ADMIN.value == "admin"


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestTokenBucket:
    """Test token bucket algorithm."""

    def test_consume_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(
            tokens=10.0,
            last_refill=time.time(),
            rate_per_second=1.0,
            max_tokens=10.0
        )

        allowed, wait_time = bucket.consume(1)

        assert allowed is True
        assert wait_time == 0
        assert bucket.tokens == 9.0

    def test_consume_failure(self):
        """Test failed token consumption."""
        bucket = TokenBucket(
            tokens=0.0,
            last_refill=time.time(),
            rate_per_second=1.0,
            max_tokens=10.0
        )

        allowed, wait_time = bucket.consume(1)

        assert allowed is False
        assert wait_time > 0

    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(
            tokens=0.0,
            last_refill=time.time() - 5,  # 5 seconds ago
            rate_per_second=1.0,
            max_tokens=10.0
        )

        allowed, _ = bucket.consume(1)

        # Should have refilled ~5 tokens
        assert allowed is True


class TestRateLimiter:
    """Test rate limiter."""

    def test_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        assert limiter.config is not None
        assert limiter._buckets == {}

    def test_init_with_config(self):
        """Test rate limiter with custom config."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=5000,
            burst_size=20
        )
        limiter = RateLimiter(config=config)

        assert limiter.config.requests_per_minute == 100
        assert limiter.config.burst_size == 20

    @pytest.mark.asyncio
    async def test_check_limit_allowed(self):
        """Test rate limit check when allowed."""
        limiter = RateLimiter(config=RateLimitConfig(
            requests_per_minute=60,
            burst_size=10
        ))

        # Create mock request with proper state
        class MockState:
            pass

        class MockClient:
            host = "127.0.0.1"

        request = MagicMock()
        request.state = MockState()
        request.headers = {}
        request.client = MockClient()

        # Should not raise
        await limiter.check_limit(request)

    @pytest.mark.asyncio
    async def test_check_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = RateLimiter(config=RateLimitConfig(
            requests_per_minute=60,
            burst_size=2  # Low burst for testing
        ))

        class MockState:
            pass

        class MockClient:
            host = "127.0.0.1"

        request = MagicMock()
        request.state = MockState()
        request.headers = {}
        request.client = MockClient()

        # Consume all tokens
        await limiter.check_limit(request)
        await limiter.check_limit(request)

        # Next request should be rate limited
        with pytest.raises(RateLimitExceeded):
            await limiter.check_limit(request)

    def test_get_stats(self):
        """Test rate limiter stats."""
        limiter = RateLimiter()
        stats = limiter.get_stats()

        assert "active_clients" in stats
        assert "total_requests" in stats
        assert "config" in stats

    def test_reset_client(self):
        """Test resetting client rate limit."""
        limiter = RateLimiter()

        # Add a bucket
        limiter._buckets["test_client"] = TokenBucket(
            tokens=0, last_refill=time.time(),
            rate_per_second=1.0, max_tokens=10.0
        )

        assert "test_client" in limiter._buckets
        assert limiter.reset_client("test_client") is True
        assert "test_client" not in limiter._buckets

    def test_reset_all(self):
        """Test resetting all rate limits."""
        limiter = RateLimiter()

        # Add some buckets
        limiter._buckets["client1"] = TokenBucket(
            tokens=0, last_refill=time.time(),
            rate_per_second=1.0, max_tokens=10.0
        )
        limiter._buckets["client2"] = TokenBucket(
            tokens=0, last_refill=time.time(),
            rate_per_second=1.0, max_tokens=10.0
        )

        limiter.reset_all()

        assert len(limiter._buckets) == 0


class TestRateLimitExceeded:
    """Test RateLimitExceeded exception."""

    def test_exception_defaults(self):
        """Test exception with defaults."""
        exc = RateLimitExceeded()

        assert exc.status_code == 429
        assert "Rate limit exceeded" in exc.detail
        assert exc.retry_after == 60

    def test_exception_custom(self):
        """Test exception with custom values."""
        exc = RateLimitExceeded(
            detail="Custom message",
            retry_after=120
        )

        assert exc.detail == "Custom message"
        assert exc.retry_after == 120


class TestRateLimitConfig:
    """Test RateLimitConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10

    def test_custom(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=2000,
            burst_size=20
        )

        assert config.requests_per_minute == 120
        assert config.requests_per_hour == 2000
        assert config.burst_size == 20


class TestGlobalInstances:
    """Test global instances."""

    def test_api_key_auth_instance(self):
        """Test global API key auth instance exists."""
        assert api_key_auth is not None
        assert isinstance(api_key_auth, APIKeyAuth)

    def test_rate_limiter_instance(self):
        """Test global rate limiter instance exists."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)
