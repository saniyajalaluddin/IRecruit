"""Rate limiting and resource protection module.

Provides in-memory sliding window rate limiting, endpoint tier protection,
HTTP headers compliance (X-RateLimit-*, Retry-After), and LLM concurrency controls.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, Request, Response
from backend.app.core.config import get_settings
from backend.app.core.errors import RateLimitExceededError


class RateLimitDecision:
    """Outcome of a rate limit check."""

    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_seconds: int,
        retry_after: int,
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_seconds = reset_seconds
        self.retry_after = retry_after


class BaseRateLimitStorage(ABC):
    """Abstract interface for rate limit storage (In-memory, Redis, etc.)."""

    @abstractmethod
    def record_and_evaluate(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        """Record an attempt and determine if request is within rate limit."""
        pass

    @abstractmethod
    def reset(self, key: Optional[str] = None) -> None:
        """Reset records for a key or all keys."""
        pass


class InMemorySlidingWindowStorage(BaseRateLimitStorage):
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self):
        # key -> list of float timestamps
        self._timestamps: Dict[str, List[float]] = defaultdict(list)

    def record_and_evaluate(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        now = time.time()
        cutoff = now - window_seconds

        # Prune old timestamps
        history = [ts for ts in self._timestamps[key] if ts > cutoff]

        if len(history) >= limit:
            oldest_relevant = history[0]
            reset_seconds = max(1, int(oldest_relevant + window_seconds - now))
            self._timestamps[key] = history
            return RateLimitDecision(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_seconds=reset_seconds,
                retry_after=reset_seconds,
            )

        # Record this attempt
        history.append(now)
        self._timestamps[key] = history

        remaining = max(0, limit - len(history))
        oldest_ts = history[0]
        reset_seconds = max(1, int(oldest_ts + window_seconds - now))

        return RateLimitDecision(
            allowed=True,
            limit=limit,
            remaining=remaining,
            reset_seconds=reset_seconds,
            retry_after=0,
        )

    def reset(self, key: Optional[str] = None) -> None:
        if key:
            self._timestamps.pop(key, None)
        else:
            self._timestamps.clear()


# Global in-memory storage instance
rate_limit_storage = InMemorySlidingWindowStorage()


class ConcurrencyThrottler:
    """Limits the number of concurrent high-resource operations (e.g., LLM inference)."""

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def acquire(self, timeout_seconds: float = 2.0) -> bool:
        """Attempt to acquire concurrency slot within timeout."""
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout_seconds)
            return True
        except asyncio.TimeoutError:
            return False

    def release(self) -> None:
        """Release acquired concurrency slot."""
        self._semaphore.release()


# Global concurrency throttler for AI operations
ai_concurrency_throttler = ConcurrencyThrottler(max_concurrent=5)


def get_client_identifier(request: Request) -> str:
    """Extract client IP or authenticated user ID for rate limiting."""
    # Check if authenticated user is present in request state
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Extract client IP with proxy awareness
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        return f"ip:{client_ip}"

    client_host = request.client.host if request.client else "127.0.0.1"
    return f"ip:{client_host}"


class RateLimiter:
    """FastAPI dependency for endpoint rate limiting."""

    def __init__(
        self,
        requests_limit: Optional[int] = None,
        window_seconds: int = 60,
        tier: str = "general",
    ):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.tier = tier

    def __call__(self, request: Request, response: Response):
        settings = get_settings()

        # Determine limit based on tier if not explicitly overridden
        if self.requests_limit is not None:
            limit = self.requests_limit
        elif self.tier == "anonymous_analysis":
            limit = settings.RATE_LIMIT_PER_MINUTE_ANONYMOUS
        elif self.tier == "authenticated_analysis":
            limit = settings.RATE_LIMIT_PER_MINUTE_AUTHENTICATED
        elif self.tier == "auth_sensitive":
            limit = 10  # Max 10 attempts per minute for auth/register
        else:
            limit = settings.RATE_LIMIT_PER_MINUTE_AUTHENTICATED

        client_id = get_client_identifier(request)
        rate_key = f"{self.tier}:{client_id}"

        decision = rate_limit_storage.record_and_evaluate(
            key=rate_key,
            limit=limit,
            window_seconds=self.window_seconds,
        )

        # Attach standard rate limit headers
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Reset"] = str(decision.reset_seconds)

        if not decision.allowed:
            response.headers["Retry-After"] = str(decision.retry_after)
            raise RateLimitExceededError(
                message=f"Rate limit exceeded for tier '{self.tier}'. Try again in {decision.retry_after} seconds.",
                details={
                    "tier": self.tier,
                    "limit": decision.limit,
                    "retry_after_seconds": decision.retry_after,
                },
            )

