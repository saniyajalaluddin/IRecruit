"""Unit tests for Phase 22: Rate Limiting & Resource Protection."""

import asyncio
import time
from unittest.mock import MagicMock
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from backend.app.core.errors import (
    RateLimitExceededError,
    app_exception_handler,
)
from backend.app.core.rate_limit import (
    ConcurrencyThrottler,
    InMemorySlidingWindowStorage,
    RateLimiter,
    get_client_identifier,
)


@pytest.fixture
def clean_storage():
    storage = InMemorySlidingWindowStorage()
    yield storage
    storage.reset()


def test_sliding_window_allows_within_limit(clean_storage):
    key = "test_client_1"
    limit = 3
    window = 10

    # 1st request
    d1 = clean_storage.record_and_evaluate(key, limit, window)
    assert d1.allowed is True
    assert d1.remaining == 2
    assert d1.limit == 3

    # 2nd request
    d2 = clean_storage.record_and_evaluate(key, limit, window)
    assert d2.allowed is True
    assert d2.remaining == 1

    # 3rd request (at limit)
    d3 = clean_storage.record_and_evaluate(key, limit, window)
    assert d3.allowed is True
    assert d3.remaining == 0

    # 4th request (exceeds limit)
    d4 = clean_storage.record_and_evaluate(key, limit, window)
    assert d4.allowed is False
    assert d4.remaining == 0
    assert d4.retry_after > 0


def test_sliding_window_resets_after_window(clean_storage):
    key = "test_client_expiry"
    limit = 2
    window = 1  # 1 second window

    d1 = clean_storage.record_and_evaluate(key, limit, window)
    d2 = clean_storage.record_and_evaluate(key, limit, window)
    assert d2.remaining == 0

    d3 = clean_storage.record_and_evaluate(key, limit, window)
    assert d3.allowed is False

    # Sleep slightly over the 1s window
    time.sleep(1.05)

    # Should be permitted again
    d4 = clean_storage.record_and_evaluate(key, limit, window)
    assert d4.allowed is True
    assert d4.remaining == 1


def test_client_identifier_resolution():
    # 1. Authenticated user
    req_auth = MagicMock(spec=Request)
    user_mock = MagicMock()
    user_mock.id = "user-12345"
    req_auth.state.user = user_mock
    assert get_client_identifier(req_auth) == "user:user-12345"

    # 2. X-Forwarded-For header
    req_proxy = MagicMock(spec=Request)
    req_proxy.state = MagicMock(spec=[])
    req_proxy.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
    assert get_client_identifier(req_proxy) == "ip:203.0.113.195"

    # 3. Direct client host
    req_direct = MagicMock(spec=Request)
    req_direct.state = MagicMock(spec=[])
    req_direct.headers = {}
    req_direct.client = MagicMock()
    req_direct.client.host = "192.168.1.50"
    assert get_client_identifier(req_direct) == "ip:192.168.1.50"


def test_rate_limiter_fastapi_endpoint_headers():
    app = FastAPI()
    app.add_exception_handler(RateLimitExceededError, app_exception_handler)

    # Setup route with strict limit of 2 requests
    limiter = RateLimiter(requests_limit=2, window_seconds=60, tier="test_route")

    @app.get("/test", dependencies=[])
    async def sample_endpoint(request: Request, response: Response):
        limiter(request, response)
        return {"status": "ok"}

    client = TestClient(app)

    # Request 1
    r1 = client.get("/test", headers={"X-Forwarded-For": "198.51.100.1"})
    assert r1.status_code == 200
    assert r1.headers.get("X-RateLimit-Limit") == "2"
    assert r1.headers.get("X-RateLimit-Remaining") == "1"

    # Request 2
    r2 = client.get("/test", headers={"X-Forwarded-For": "198.51.100.1"})
    assert r2.status_code == 200
    assert r2.headers.get("X-RateLimit-Remaining") == "0"

    # Request 3 - Must fail with 429
    r3 = client.get("/test", headers={"X-Forwarded-For": "198.51.100.1"})
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers
    data = r3.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_concurrency_throttler():
    throttler = ConcurrencyThrottler(max_concurrent=2)

    # First 2 acquire immediately
    acquired_1 = await throttler.acquire(timeout_seconds=0.1)
    acquired_2 = await throttler.acquire(timeout_seconds=0.1)
    assert acquired_1 is True
    assert acquired_2 is True

    # 3rd acquire times out
    acquired_3 = await throttler.acquire(timeout_seconds=0.05)
    assert acquired_3 is False

    # Release one
    throttler.release()

    # Now 4th acquire succeeds
    acquired_4 = await throttler.acquire(timeout_seconds=0.1)
    assert acquired_4 is True

    # Clean up releases
    throttler.release()
    throttler.release()
