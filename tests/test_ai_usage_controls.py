"""Unit tests for Phase 23: AI Cost and Usage Controls."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.usage import UsageRecord
from backend.app.modules.usage.pricing import calculate_cost
from backend.app.modules.usage.schemas import (
    UsageQuota,
    UsageRecordCreate,
)
from backend.app.modules.usage.service import (
    QuotaExceededError,
    UsageTrackingService,
)
from backend.app.modules.usage.token_counter import (
    estimate_tokens,
    truncate_to_token_limit,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def fresh_usage_service():
    return UsageTrackingService()


def test_calculate_cost():
    # 10,000 input tokens and 2,000 output tokens on gpt-4o
    # input: 10,000 * 5/1M = $0.05
    # output: 2,000 * 15/1M = $0.03
    # total = $0.08
    cost_gpt4o = calculate_cost("gpt-4o", input_tokens=10_000, output_tokens=2_000)
    assert cost_gpt4o == pytest.approx(0.08, abs=1e-5)

    # Free models should produce exactly $0.00
    assert calculate_cost("ollama", 50_000, 10_000) == 0.0
    assert calculate_cost("mock-llm", 25_000, 5_000) == 0.0


def test_token_counter_and_truncation():
    sample_text = "Experienced Senior Software Engineer with deep skills in Python, FastAPI, and Kubernetes."
    tokens = estimate_tokens(sample_text)
    assert tokens > 10
    assert tokens < 40

    # Truncate to very small budget
    truncated = truncate_to_token_limit(sample_text, max_tokens=5)
    assert len(truncated) < len(sample_text)
    assert "Content truncated" in truncated

    # Truncate with large budget preserves text
    untouched = truncate_to_token_limit(sample_text, max_tokens=100)
    assert untouched == sample_text


def test_usage_tracking_and_summary(fresh_usage_service):
    user_id = "user-abc-123"

    # Record 1st call
    rec1 = UsageRecordCreate(
        user_id=user_id,
        provider_name="openai",
        model_name="gpt-4o-mini",
        input_tokens=1_000,
        output_tokens=500,
        latency_ms=250.0,
    )
    u1 = fresh_usage_service.record_usage(rec1)
    assert u1.total_tokens == 1500
    assert u1.estimated_cost_usd > 0.0

    # Record 2nd call
    rec2 = UsageRecordCreate(
        user_id=user_id,
        provider_name="google",
        model_name="gemini-1.5-flash",
        input_tokens=2_000,
        output_tokens=1_000,
        latency_ms=300.0,
    )
    u2 = fresh_usage_service.record_usage(rec2)
    assert u2.total_tokens == 3000

    # Verify summary
    summary = fresh_usage_service.get_summary(user_id)
    assert summary.total_calls == 2
    assert summary.total_input_tokens == 3000
    assert summary.total_output_tokens == 1500
    assert summary.total_tokens == 4500
    assert summary.total_cost_usd == pytest.approx(u1.estimated_cost_usd + u2.estimated_cost_usd, abs=1e-5)


def test_quota_limits_enforced(fresh_usage_service):
    user_id = "user-budget-test"

    # Set strict quota: max 1,000 tokens daily
    fresh_usage_service.set_quota(
        user_id,
        UsageQuota(daily_token_limit=1_000, monthly_cost_limit_usd=1.00),
    )

    # 500 tokens should be allowed
    fresh_usage_service.check_quota(user_id, projected_tokens=500)

    # Consume 800 tokens
    fresh_usage_service.record_usage(
        UsageRecordCreate(
            user_id=user_id,
            provider_name="mock",
            model_name="mock",
            input_tokens=500,
            output_tokens=300,
        )
    )

    # Another 300 tokens exceeds 1,000 (800 + 300 = 1100 > 1000)
    with pytest.raises(QuotaExceededError) as exc_info:
        fresh_usage_service.check_quota(user_id, projected_tokens=300)

    assert "Daily AI token limit" in str(exc_info.value.message)
    assert exc_info.value.status_code == 429


def test_database_persistence_of_usage(fresh_usage_service, in_memory_db):
    rec = UsageRecordCreate(
        user_id="user-db-test",
        session_id="session-xyz",
        analysis_id="analysis-789",
        provider_name="openai",
        model_name="gpt-4o",
        input_tokens=1200,
        output_tokens=400,
        latency_ms=180.5,
    )

    usage = fresh_usage_service.record_usage(rec, db=in_memory_db)
    assert usage.total_tokens == 1600

    # Query from database to verify persistence
    row = in_memory_db.query(UsageRecord).filter_by(analysis_id="analysis-789").first()
    assert row is not None
    assert row.provider_name == "openai"
    assert row.model_name == "gpt-4o"
    assert row.total_tokens == 1600
    assert row.latency_ms == pytest.approx(180.5)
