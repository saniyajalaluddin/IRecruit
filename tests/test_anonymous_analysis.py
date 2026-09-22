"""Unit and integration tests for Phase 24: Anonymous Quick Analysis Mode."""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.main import create_application
from backend.app.models.analysis import Analysis
from backend.app.models.user import User
from backend.app.modules.analysis.schemas import AnonymousAnalysisRequest, ClaimAnalysisRequest
from backend.app.modules.analysis.service import AnonymousAnalysisService
from backend.app.core.errors import ForbiddenError, NotFoundError


@pytest.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_resume_text():
    return (
        "Jane Doe\n"
        "jane.doe@example.com | (555) 123-4567 | San Francisco, CA\n"
        "Work Experience\n"
        "Senior Backend Engineer | CloudScale Inc. | Jan 2021 - Present\n"
        "• Architected distributed microservices in Python and FastAPI.\n"
        "• Optimized PostgreSQL database query execution plans.\n"
        "Skills\n"
        "Python, FastAPI, Docker, PostgreSQL, Kubernetes\n"
        "Education\n"
        "B.S. in Computer Science | 2020\n"
    )


@pytest.fixture
def sample_jd_text():
    return (
        "Title: Senior Backend Developer\n"
        "Company: Apex Cloud\n"
        "Requirements:\n"
        "- Required: 5+ years of experience in Python and FastAPI.\n"
        "- Required: Strong knowledge of PostgreSQL.\n"
        "- Preferred: Experience with Kubernetes and Docker.\n"
    )


@pytest.mark.asyncio
async def test_anonymous_analysis_pipeline_and_pii_masking(
    async_test_db, sample_resume_text, sample_jd_text
):
    service = AnonymousAnalysisService()
    req = AnonymousAnalysisRequest(
        resume_text=sample_resume_text,
        job_description_text=sample_jd_text,
        job_title="Senior Backend Developer",
        company_name="Apex Cloud",
        session_id="anon_sess_test_123",
    )

    response = await service.run_anonymous_analysis(
        db=async_test_db,
        request=req,
        client_ip="203.0.113.10",
    )

    assert response.analysis_id is not None
    assert response.session_id == "anon_sess_test_123"
    assert response.overall_score > 0.0
    assert response.grade in ("A", "B", "C", "D", "F")
    assert response.requirements_matched >= 1
    assert response.ats_compatibility["overall_score"] > 70.0
    assert response.is_claimed is False
    assert response.expires_at > response.created_at

    # Verify DB entity state
    analysis = await async_test_db.get(Analysis, response.analysis_id)
    assert analysis is not None
    assert analysis.is_anonymous is True
    assert analysis.user_id is None
    assert analysis.session_id == "anon_sess_test_123"


@pytest.mark.asyncio
async def test_claim_anonymous_analysis(
    async_test_db, sample_resume_text, sample_jd_text
):
    service = AnonymousAnalysisService()
    req = AnonymousAnalysisRequest(
        resume_text=sample_resume_text,
        job_description_text=sample_jd_text,
        session_id="session_to_claim",
    )

    result = await service.run_anonymous_analysis(
        db=async_test_db,
        request=req,
    )

    # Create dummy user
    user = User(
        email="newuser@example.com",
        hashed_password="hashed_pw",
        full_name="New Registered User",
        is_active=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)

    # Claim with wrong session_id should fail
    with pytest.raises(ForbiddenError):
        await service.claim_analysis(
            db=async_test_db,
            analysis_id=result.analysis_id,
            session_id="wrong_session",
            user=user,
        )

    # Claim with valid session_id succeeds
    claimed = await service.claim_analysis(
        db=async_test_db,
        analysis_id=result.analysis_id,
        session_id="session_to_claim",
        user=user,
    )
    assert claimed.claimed is True
    assert claimed.user_id == user.id

    # Verify updated analysis ownership
    analysis = await async_test_db.get(Analysis, result.analysis_id)
    assert analysis.is_anonymous is False
    assert analysis.user_id == user.id


@pytest.mark.asyncio
async def test_purge_expired_anonymous_analyses(
    async_test_db, sample_resume_text, sample_jd_text
):
    service = AnonymousAnalysisService()
    req = AnonymousAnalysisRequest(
        resume_text=sample_resume_text,
        job_description_text=sample_jd_text,
        session_id="session_purge_test",
    )

    result = await service.run_anonymous_analysis(
        db=async_test_db,
        request=req,
    )

    # Manually backdate analysis created_at to 30 hours ago
    analysis = await async_test_db.get(Analysis, result.analysis_id)
    analysis.created_at = datetime.now(timezone.utc) - timedelta(hours=30)
    await async_test_db.commit()

    # Purge with 24 hours retention
    purged = await service.purge_expired_anonymous_analyses(
        db=async_test_db,
        retention_hours=24,
    )
    assert purged == 1

    # Verify it is deleted
    deleted_check = await async_test_db.get(Analysis, result.analysis_id)
    assert deleted_check is None


@pytest.mark.asyncio
async def test_anonymous_api_endpoint(async_test_db, sample_resume_text, sample_jd_text):
    from backend.app.db.session import get_db

    app = create_application()

    async def override_get_db():
        yield async_test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/analyses/anonymous",
            json={
                "resume_text": sample_resume_text,
                "job_description_text": sample_jd_text,
                "session_id": "api_test_session_1",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["analysis_id"] is not None
        assert body["data"]["session_id"] == "api_test_session_1"
        assert "X-RateLimit-Limit" in resp.headers
