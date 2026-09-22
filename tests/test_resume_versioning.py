"""Unit and integration tests for Phase 26: Resume Versioning and Iteration Tracking."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.errors import ForbiddenError, NotFoundError, ValidationError
from backend.app.db.base import Base
from backend.app.main import create_application
from backend.app.models.analysis import Analysis
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.versioning.service import ResumeVersioningService


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
        email="candidate.v@example.com",
        hashed_password="hashed_password",
        full_name="Candidate Versioning",
        is_active=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)
    return user


@pytest.fixture
async def initial_resume(async_test_db, test_user) -> Resume:
    resume = Resume(
        user_id=test_user.id,
        title="Software Engineer Resume",
        original_filename="resume_v1.txt",
        file_path="memory://v1",
        file_size_bytes=200,
        content_type="text/plain",
        is_anonymous=False,
    )
    async_test_db.add(resume)
    await async_test_db.flush()

    v1 = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        raw_text="Jane Doe\njane@example.com\nSoftware Engineer with Python and Docker experience.\nBuilt web servers.",
        pii_masked_text="Jane Doe\n[REDACTED_EMAIL]\nSoftware Engineer with Python and Docker experience.\nBuilt web servers.",
        structured_data={"skills": ["Python", "Docker"]},
    )
    async_test_db.add(v1)
    await async_test_db.commit()
    await async_test_db.refresh(resume)
    return resume


@pytest.mark.asyncio
async def test_create_and_list_resume_versions(async_test_db, test_user, initial_resume):
    service = ResumeVersioningService()

    v2_text = (
        "Jane Doe\njane@example.com\n"
        "Senior Software Engineer with Python, Docker, and Kubernetes experience.\n"
        "Architected distributed cloud systems handling 10M requests daily."
    )

    # Create v2
    v2_item = await service.create_version(
        db=async_test_db,
        resume_id=initial_resume.id,
        user=test_user,
        raw_text=v2_text,
        notes="Added Kubernetes and cloud scale metrics",
    )

    assert v2_item.version_number == 2
    assert v2_item.word_count > 10

    # List versions
    history = await service.list_versions(
        db=async_test_db,
        resume_id=initial_resume.id,
        user=test_user,
    )

    assert history.total_versions == 2
    assert history.versions[0].version_number == 1
    assert history.versions[1].version_number == 2


@pytest.mark.asyncio
async def test_compare_resume_versions(async_test_db, test_user, initial_resume):
    service = ResumeVersioningService()

    v2_text = (
        "Jane Doe\njane@example.com\n"
        "Senior Software Engineer with Python, Docker, and Kubernetes experience.\n"
        "Architected distributed cloud systems handling 10M requests daily."
    )

    await service.create_version(
        db=async_test_db,
        resume_id=initial_resume.id,
        user=test_user,
        raw_text=v2_text,
    )

    # Same version compare raises ValidationError
    with pytest.raises(ValidationError):
        await service.compare_versions(
            db=async_test_db,
            resume_id=initial_resume.id,
            user=test_user,
            base_version_number=1,
            target_version_number=1,
        )

    # Compare v1 vs v2
    comparison = await service.compare_versions(
        db=async_test_db,
        resume_id=initial_resume.id,
        user=test_user,
        base_version_number=1,
        target_version_number=2,
    )

    assert comparison.base_version_number == 1
    assert comparison.target_version_number == 2
    assert len(comparison.text_diffs) > 0

    # Verify added line detected
    added_diffs = [d.text for d in comparison.text_diffs if d.change_type == "added"]
    assert any("Kubernetes" in t for t in added_diffs)


@pytest.mark.asyncio
async def test_compare_with_score_progression(async_test_db, test_user, initial_resume):
    service = ResumeVersioningService()

    v2_text = "Jane Doe\nPython, Docker, Kubernetes\nArchitected cloud clusters."
    await service.create_version(
        db=async_test_db,
        resume_id=initial_resume.id,
        user=test_user,
        raw_text=v2_text,
    )

    # Get versions
    history = await service.list_versions(async_test_db, initial_resume.id, test_user)
    v1_id = history.versions[0].id
    v2_id = history.versions[1].id

    # Add mock analysis for v1 (score 70.0) and v2 (score 85.0)
    a1 = Analysis(
        user_id=test_user.id,
        resume_id=initial_resume.id,
        resume_version_id=v1_id,
        job_description_id="dummy-jd-id",
        overall_score=70.0,
        component_scores={},
        weights={},
        scoring_version="v1.0.0",
        prompt_version="v1.0.0",
        llm_provider="mock",
        llm_model="mock",
        embedding_provider="mock",
        embedding_model="mock",
        is_anonymous=False,
    )
    a2 = Analysis(
        user_id=test_user.id,
        resume_id=initial_resume.id,
        resume_version_id=v2_id,
        job_description_id="dummy-jd-id",
        overall_score=85.0,
        component_scores={},
        weights={},
        scoring_version="v1.0.0",
        prompt_version="v1.0.0",
        llm_provider="mock",
        llm_model="mock",
        embedding_provider="mock",
        embedding_model="mock",
        is_anonymous=False,
    )
    async_test_db.add(a1)
    async_test_db.add(a2)
    await async_test_db.commit()

    comparison = await service.compare_versions(
        async_test_db, initial_resume.id, test_user, base_version_number=1, target_version_number=2
    )

    assert comparison.score_progression is not None
    assert comparison.score_progression.base_score == 70.0
    assert comparison.score_progression.target_score == 85.0
    assert comparison.score_progression.delta == 15.0
    assert comparison.score_progression.target_grade == "B"


@pytest.mark.asyncio
async def test_versioning_endpoints(async_test_db, test_user, initial_resume):
    from backend.app.db.session import get_db

    app = create_application()

    async def override_get_db():
        yield async_test_db

    async def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create version endpoint
        post_resp = await client.post(
            f"/api/v1/resumes/{initial_resume.id}/versions",
            json={"raw_text": "Updated resume text for version 2 testing."},
        )
        assert post_resp.status_code == 201
        assert post_resp.json()["data"]["version_number"] == 2

        # List versions endpoint
        list_resp = await client.get(f"/api/v1/resumes/{initial_resume.id}/versions")
        assert list_resp.status_code == 200
        assert list_resp.json()["data"]["total_versions"] == 2

        # Compare versions endpoint
        comp_resp = await client.get(
            f"/api/v1/resumes/{initial_resume.id}/compare?base_version=1&target_version=2"
        )
        assert comp_resp.status_code == 200
        assert comp_resp.json()["data"]["base_version_number"] == 1
        assert comp_resp.json()["data"]["target_version_number"] == 2
