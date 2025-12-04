"""
TrustChain Rate Limiting

Provides request rate limiting for API protection.

Features:
- Token bucket algorithm
- Per-client rate limits (based on API key or IP)
- Configurable limits per endpoint
- Rate limit headers in responses

Usage:
    from middleware.rate_limit import rate_limiter, RateLimitConfig

    @app.get("/api/resource")
    async def get_resource(
        request: Request,
        _: None = Depends(rate_limiter.check_limit)
    ):
        return {"data": "..."}

Built with care by Kareem & Claude
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: int = 60
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)}
        )
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Allow burst of requests


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_refill: float
    rate_per_second: float
    max_tokens: float

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens.

        Returns:
            Tuple of (success, wait_time_seconds)
        """
        now = time.time()

        # Refill tokens based on time passed
        time_passed = now - self.last_refill
        new_tokens = time_passed * self.rate_per_second
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0

        # Calculate wait time
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.rate_per_second

        return False, wait_time


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Tracks requests per client (by API key or IP address).
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig(
            requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS", "60")),
            requests_per_hour=int(os.getenv("RATE_LIMIT_REQUESTS_HOUR", "1000")),
            burst_size=int(os.getenv("RATE_LIMIT_BURST", "10"))
        )

        # Token buckets per client
        self._buckets: Dict[str, TokenBucket] = {}

        # Request counts for monitoring
        self._request_counts: Dict[str, int] = defaultdict(int)

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request.

        Uses API key if available, otherwise IP address.
        """
        # Check for API key in request state
        if hasattr(request.state, "api_key_info") and request.state.api_key_info:
            return f"key:{request.state.api_key_info.key_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _get_bucket(self, client_id: str, rate_per_minute: int) -> TokenBucket:
        """Get or create token bucket for client."""
        if client_id not in self._buckets:
            rate_per_second = rate_per_minute / 60.0
            self._buckets[client_id] = TokenBucket(
                tokens=float(self.config.burst_size),
                last_refill=time.time(),
                rate_per_second=rate_per_second,
                max_tokens=float(self.config.burst_size)
            )
        return self._buckets[client_id]

    def _get_rate_limit(self, request: Request) -> int:
        """
        Get rate limit for request.

        Uses API key's rate limit if available, otherwise default.
        """
        if hasattr(request.state, "api_key_info") and request.state.api_key_info:
            return request.state.api_key_info.rate_limit_per_minute

        return self.config.requests_per_minute

    async def check_limit(self, request: Request) -> None:
        """
        Check if request is within rate limit.

        Raises RateLimitExceeded if limit exceeded.
        """
        client_id = self._get_client_id(request)
        rate_limit = self._get_rate_limit(request)

        bucket = self._get_bucket(client_id, rate_limit)
        allowed, wait_time = bucket.consume(1)

        # Track request
        self._request_counts[client_id] += 1

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded. Try again in {int(wait_time)} seconds.",
                retry_after=int(wait_time) + 1
            )

        # Add rate limit headers to response (via request state)
        request.state.rate_limit_info = {
            "limit": rate_limit,
            "remaining": int(bucket.tokens),
            "reset": int(time.time() + 60)
        }

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "active_clients": len(self._buckets),
            "total_requests": sum(self._request_counts.values()),
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "burst_size": self.config.burst_size
            }
        }

    def reset_client(self, client_id: str) -> bool:
        """Reset rate limit for a specific client."""
        if client_id in self._buckets:
            del self._buckets[client_id]
            return True
        return False

    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._buckets.clear()
        self._request_counts.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()


def add_rate_limit_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """
    Add rate limit headers to response.

    Headers:
        X-RateLimit-Limit: Maximum requests per minute
        X-RateLimit-Remaining: Remaining requests in current window
        X-RateLimit-Reset: Unix timestamp when limit resets
    """
    if hasattr(request.state, "rate_limit_info"):
        info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

    return response
