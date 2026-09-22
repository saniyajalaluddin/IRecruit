"""Unit and integration tests for Phase 25: Authenticated Analysis History & Dashboard Limits."""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.main import create_application
from backend.app.models.analysis import Analysis
from backend.app.models.evidence import Evidence
from backend.app.models.job_description import JobDescription
from backend.app.models.requirement import Requirement
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.dashboard.service import DashboardService


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
async def test_user(async_test_db) -> User:
    user = User(
        email="candidate@example.com",
        hashed_password="hashed_pw",
        full_name="Jane Candidate",
        is_active=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)
    return user


async def create_mock_analysis(
    db: AsyncSession,
    user_id: str,
    score: float,
    created_at: datetime,
    missing_skills: list,
) -> Analysis:
    resume = Resume(
        user_id=user_id,
        title="Resume",
        original_filename="resume.txt",
        file_path="memory://",
        file_size_bytes=100,
        content_type="text/plain",
    )
    db.add(resume)
    await db.flush()

    ver = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        raw_text="Sample text",
        pii_masked_text="Sample text",
        structured_data={},
    )
    db.add(ver)
    await db.flush()

    jd = JobDescription(
        user_id=user_id,
        title=f"Role with score {score}",
        company_name="Tech Co",
        raw_text="JD text",
        structured_requirements=[],
    )
    db.add(jd)
    await db.flush()

    analysis = Analysis(
        user_id=user_id,
        resume_id=resume.id,
        resume_version_id=ver.id,
        job_description_id=jd.id,
        overall_score=score,
        component_scores={"technical_skill_alignment": score},
        weights={},
        scoring_version="v1.0.0",
        prompt_version="v1.0.0",
        llm_provider="mock",
        llm_model="mock-llm",
        embedding_provider="mock",
        embedding_model="mock",
        is_anonymous=False,
    )
    analysis.created_at = created_at
    db.add(analysis)
    await db.flush()

    # Add missing requirement and evidence
    for skill in missing_skills:
        req = Requirement(
            analysis_id=analysis.id,
            requirement_text=f"Must have experience in {skill}",
            category="technical_skill",
            priority="required",
            normalized_terms=[skill.lower()],
        )
        db.add(req)
        await db.flush()

        ev = Evidence(
            analysis_id=analysis.id,
            requirement_id=req.id,
            classification="MISSING",
            snippets=[],
            explanation="No supporting evidence was found in the submitted resume.",
            has_evidence=False,
        )
        db.add(ev)

    await db.commit()
    return analysis


@pytest.mark.asyncio
async def test_free_tier_enforces_latest_5_analyses(async_test_db, test_user):
    service = DashboardService()
    now = datetime.now(timezone.utc)

    # Create 7 analyses with increasing timestamps and scores
    for i in range(7):
        await create_mock_analysis(
            db=async_test_db,
            user_id=test_user.id,
            score=50.0 + (i * 5),
            created_at=now - timedelta(days=7 - i),
            missing_skills=["Kubernetes", "AWS"],
        )

    # Query history
    history = await service.get_analysis_history(db=async_test_db, user_id=test_user.id)

    assert history.total_saved == 7
    assert history.max_allowed == 5
    assert len(history.items) == 5

    # Should be ordered newest to oldest
    scores = [item.overall_score for item in history.items]
    assert scores == [80.0, 75.0, 70.0, 65.0, 60.0]


@pytest.mark.asyncio
async def test_dashboard_metrics_aggregation(async_test_db, test_user):
    service = DashboardService()
    now = datetime.now(timezone.utc)

    # Create 3 analyses
    await create_mock_analysis(
        async_test_db, test_user.id, score=80.0, created_at=now - timedelta(days=2), missing_skills=["Docker", "AWS"]
    )
    await create_mock_analysis(
        async_test_db, test_user.id, score=90.0, created_at=now - timedelta(days=1), missing_skills=["Docker", "Kafka"]
    )
    await create_mock_analysis(
        async_test_db, test_user.id, score=70.0, created_at=now, missing_skills=["Docker"]
    )

    metrics = await service.get_dashboard_metrics(db=async_test_db, user_id=test_user.id)

    assert metrics.total_analyses_run == 3
    assert metrics.average_score == 80.0  # (80 + 90 + 70) / 3
    # Docker appeared in all 3 missing lists
    assert metrics.top_missing_skills[0] == "docker"
    assert metrics.latest_analysis.overall_score == 70.0


@pytest.mark.asyncio
async def test_history_and_dashboard_endpoints(async_test_db, test_user):
    from backend.app.db.session import get_db

    now = datetime.now(timezone.utc)
    await create_mock_analysis(
        async_test_db, test_user.id, score=85.0, created_at=now, missing_skills=["Redis"]
    )

    app = create_application()

    async def override_get_db():
        yield async_test_db

    async def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # History
        hist_resp = await client.get("/api/v1/analyses/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["success"] is True
        assert len(hist_data["data"]["items"]) == 1
        assert hist_data["data"]["items"][0]["overall_score"] == 85.0

        # Dashboard
        dash_resp = await client.get("/api/v1/analyses/dashboard")
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert dash_data["success"] is True
        assert dash_data["data"]["total_analyses_run"] == 1
        assert dash_data["data"]["average_score"] == 85.0
        assert "redis" in dash_data["data"]["top_missing_skills"]

