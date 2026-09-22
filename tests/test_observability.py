"""Unit and integration tests for Phase 27: Observability, Tracing, and Telemetry."""

import logging
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.logging import PrivacyFilter
from backend.app.db.base import Base
from backend.app.main import create_application
from backend.app.modules.observability.metrics import (
    PerformanceTracker,
    TelemetryCollector,
    telemetry,
)


@pytest.fixture
def clean_telemetry():
    collector = TelemetryCollector()
    yield collector
    collector.reset()


@pytest.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_telemetry_collector_percentiles_and_errors(clean_telemetry):
    # Record 100 requests with latencies from 1ms to 100ms
    for i in range(1, 101):
        status = 200 if i <= 95 else 500  # 5% error rate
        clean_telemetry.record_request(
            method="POST",
            path="/api/v1/analyses",
            status_code=status,
            duration_ms=float(i),
        )

    summary = clean_telemetry.get_summary()

    assert summary["total_requests"] == 100
    assert summary["error_count"] == 5
    assert summary["error_rate"] == 0.05
    assert summary["status_codes"][200] == 95
    assert summary["status_codes"][500] == 5

    # p50 ~ 50ms, p95 ~ 95ms, p99 ~ 99ms
    assert summary["latency_p50_ms"] == pytest.approx(50.0, abs=1.0)
    assert summary["latency_p95_ms"] == pytest.approx(95.0, abs=1.0)
    assert summary["latency_p99_ms"] == pytest.approx(99.0, abs=1.0)


def test_performance_tracker_stages():
    tracker = PerformanceTracker(analysis_id="analysis-trace-789")
    tracker.record_stage("parsing", 12.5)
    tracker.record_stage("matching", 45.2)
    tracker.record_stage("scoring", 8.1)
    tracker.record_tokens(350)

    summary = tracker.finish()

    assert summary.analysis_id == "analysis-trace-789"
    assert summary.stages["parsing"] == 12.5
    assert summary.stages["matching"] == 45.2
    assert summary.stages["scoring"] == 8.1
    assert summary.tokens_used == 350
    assert summary.total_duration_ms >= 0.0


def test_privacy_log_filter_masking():
    log_filter = PrivacyFilter()

    # 1. Email masking
    masked_email = log_filter.mask_string("Failed login attempt for user alex.smith@domain.org on web.")
    assert "alex.smith@domain.org" not in masked_email
    assert "[REDACTED_EMAIL]" in masked_email

    # 2. Bearer token masking
    jwt_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG"
    masked_jwt = log_filter.mask_string(f"Header: {jwt_token}")
    assert "eyJhbGci" not in masked_jwt
    assert "[REDACTED_TOKEN]" in masked_jwt

    # 3. Sensitive dictionary key masking
    data = {
        "user_email": "candidate@work.com",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-1234567890abcdef",
        "nested": {"client_secret": "my-secret-val"},
    }
    masked_dict = log_filter.mask_dict(data)
    assert masked_dict["password"] == "[REDACTED]"
    assert masked_dict["api_key"] == "[REDACTED]"
    assert masked_dict["nested"]["client_secret"] == "[REDACTED]"
    assert "[REDACTED_EMAIL]" in masked_dict["user_email"]


@pytest.mark.asyncio
async def test_health_and_telemetry_endpoints(async_test_db):
    from backend.app.db.session import get_db

    app = create_application()

    async def override_get_db():
        yield async_test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check with DB status
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["telemetry"] is not None

        # 2. Telemetry endpoint
        tel_resp = await client.get("/api/v1/health/telemetry")
        assert tel_resp.status_code == 200
        tel_data = tel_resp.json()["data"]
        assert "total_requests" in tel_data
        assert "latency_p50_ms" in tel_data

