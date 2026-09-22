"""Comprehensive tests for database models, constraints, relationships, and cascade deletions."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.db.base import Base
from backend.app.models import (
    Analysis,
    AuditEvent,
    Entitlement,
    Evidence,
    JobDescription,
    Recommendation,
    Requirement,
    Resume,
    ResumeVersion,
    UsageRecord,
    User,
)


@pytest_asyncio.fixture(loop_scope="function")
async def db_session():
    """In-memory SQLite async session fixture with all tables pre-created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_creation_and_retrieval(db_session: AsyncSession):
    """Verify User model creation, persistence, and retrieval."""
    user = User(
        email="candidate.test@example.com",
        hashed_password="fakehashedpassword",
        full_name="Alex Candidate",
        role="candidate",
    )
    db_session.add(user)
    await db_session.commit()

    # Query back
    stmt = select(User).where(User.email == "candidate.test@example.com")
    result = await db_session.execute(stmt)
    retrieved = result.scalar_one_or_none()

    assert retrieved is not None
    assert retrieved.full_name == "Alex Candidate"
    assert retrieved.is_active is True
    assert retrieved.created_at is not None


@pytest.mark.asyncio
async def test_user_email_unique_constraint(db_session: AsyncSession):
    """Verify duplicate email throws IntegrityError constraint violation."""
    user1 = User(
        email="unique@example.com",
        hashed_password="hash1",
        full_name="User One",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        email="unique@example.com",
        hashed_password="hash2",
        full_name="User Two",
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_full_domain_relationships_and_cascading(db_session: AsyncSession):
    """Verify complete relational hierarchy from User to Analysis, Evidence, and Recommendations."""
    # 1. Create User
    user = User(
        email="dev@example.com",
        hashed_password="securepasswordhash",
        full_name="Developer Jane",
    )
    db_session.add(user)
    await db_session.flush()

    # 2. Create Resume & ResumeVersion
    resume = Resume(
        user_id=user.id,
        title="Software Engineer Resume",
        original_filename="jane_resume.pdf",
        file_path="/storage/temp/jane_resume.pdf",
        file_size_bytes=102400,
        content_type="application/pdf",
    )
    db_session.add(resume)
    await db_session.flush()

    version = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        raw_text="Jane Developer: Python, FastAPI, Docker",
        pii_masked_text="[REDACTED_NAME]: Python, FastAPI, Docker",
        structured_data={"skills": ["Python", "FastAPI", "Docker"]},
    )
    db_session.add(version)
    await db_session.flush()

    # 3. Create Job Description
    jd = JobDescription(
        user_id=user.id,
        title="Senior Backend Engineer",
        company_name="TechCorp",
        raw_text="Must have Python, FastAPI, Docker, and Kubernetes.",
        structured_requirements={"required_skills": ["Python", "FastAPI", "Docker", "Kubernetes"]},
    )
    db_session.add(jd)
    await db_session.flush()

    # 4. Create Analysis
    analysis = Analysis(
        user_id=user.id,
        resume_id=resume.id,
        resume_version_id=version.id,
        job_description_id=jd.id,
        overall_score=85.0,
        component_scores={"technical": 90.0, "semantic": 80.0},
        weights={"technical": 0.5, "semantic": 0.5},
        scoring_version="v1.0.0",
        prompt_version="v1.0.0",
        llm_provider="mock",
        llm_model="mock-v1",
        embedding_provider="mock",
        embedding_model="mock-embed-v1",
        execution_duration_ms=45.2,
    )
    db_session.add(analysis)
    await db_session.flush()

    # 5. Create Requirement, Evidence, and Recommendation
    req = Requirement(
        analysis_id=analysis.id,
        requirement_text="Must have 3+ years Python experience",
        category="technical_skill",
        priority="required",
        normalized_terms=["python"],
    )
    db_session.add(req)
    await db_session.flush()

    ev = Evidence(
        analysis_id=analysis.id,
        requirement_id=req.id,
        classification="MATCHED",
        snippets=[{"quote": "Python, FastAPI", "source": "skills"}],
        explanation="Candidate explicitly lists Python under technical skills.",
        has_evidence=True,
    )
    db_session.add(ev)

    rec = Recommendation(
        analysis_id=analysis.id,
        requirement_id=req.id,
        recommendation_type="clarify_experience",
        title="Quantify Python project achievements",
        rationale="Python is verified in skills but could include measurable impact.",
        is_evidence_grounded=True,
    )
    db_session.add(rec)

    # 6. AuditEvent, UsageRecord, and Entitlement
    audit = AuditEvent(
        user_id=user.id,
        event_type="analysis_created",
        resource_type="analysis",
        resource_id=analysis.id,
        details={"score": "85.0"},
    )
    db_session.add(audit)

    usage = UsageRecord(
        user_id=user.id,
        analysis_id=analysis.id,
        provider_name="mock",
        model_name="mock-v1",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        latency_ms=45.2,
    )
    db_session.add(usage)

    entitlement = Entitlement(
        user_id=user.id,
        tier="free",
        max_saved_analyses=5,
        analyses_count=1,
    )
    db_session.add(entitlement)

    await db_session.commit()

    # Retrieve analysis with requirements and evidence
    stmt = select(Analysis).where(Analysis.id == analysis.id)
    res = await db_session.execute(stmt)
    saved_analysis = res.scalar_one()
    assert saved_analysis.overall_score == 85.0
    assert saved_analysis.llm_provider == "mock"

    # Test Cascade Deletion: Deleting user must cascade and delete associated resumes, versions, and analyses
    await db_session.delete(user)
    await db_session.commit()

    # Verify Analysis and Resume are deleted
    check_analysis = await db_session.execute(select(Analysis).where(Analysis.id == analysis.id))
    assert check_analysis.scalar_one_or_none() is None

    check_resume = await db_session.execute(select(Resume).where(Resume.id == resume.id))
    assert check_resume.scalar_one_or_none() is None

    check_requirements = await db_session.execute(select(Requirement).where(Requirement.analysis_id == analysis.id))
    assert check_requirements.scalar_one_or_none() is None
