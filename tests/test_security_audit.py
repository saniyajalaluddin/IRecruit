"""Comprehensive security hardening and penetration testing audit suite."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.errors import ForbiddenError
from backend.app.db.base import Base
from backend.app.main import create_application
from backend.app.models.analysis import Analysis
from backend.app.models.job_description import JobDescription
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.documents.sanitizer import sanitize_filename
from backend.app.modules.security.authorization import verify_analysis_ownership, verify_resume_ownership


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
async def victim_user(async_test_db) -> User:
    user = User(
        email="victim@company.org",
        hashed_password="hashed_pw_victim",
        full_name="Victim User",
        is_active=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)
    return user


@pytest.fixture
async def attacker_user(async_test_db) -> User:
    user = User(
        email="attacker@adversary.net",
        hashed_password="hashed_pw_attacker",
        full_name="Attacker User",
        is_active=True,
    )
    async_test_db.add(user)
    await async_test_db.commit()
    await async_test_db.refresh(user)
    return user


@pytest.fixture
async def victim_resume(async_test_db, victim_user) -> Resume:
    resume = Resume(
        user_id=victim_user.id,
        title="Victim Confidential Resume",
        original_filename="confidential_resume.pdf",
        file_path="memory://victim",
        file_size_bytes=150,
        content_type="application/pdf",
        is_anonymous=False,
    )
    async_test_db.add(resume)
    await async_test_db.commit()
    await async_test_db.refresh(resume)
    return resume


@pytest.fixture
async def victim_analysis(async_test_db, victim_user, victim_resume) -> Analysis:
    ver = ResumeVersion(
        resume_id=victim_resume.id,
        version_number=1,
        raw_text="Confidential text",
        pii_masked_text="Confidential text",
        structured_data={},
    )
    async_test_db.add(ver)
    await async_test_db.flush()

    jd = JobDescription(
        user_id=victim_user.id,
        title="Executive Role",
        raw_text="Confidential JD",
        structured_requirements=[],
    )
    async_test_db.add(jd)
    await async_test_db.flush()

    analysis = Analysis(
        user_id=victim_user.id,
        resume_id=victim_resume.id,
        resume_version_id=ver.id,
        job_description_id=jd.id,
        overall_score=92.0,
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
    async_test_db.add(analysis)
    await async_test_db.commit()
    await async_test_db.refresh(analysis)
    return analysis


# 1. IDOR (Horizontal Privilege Escalation) Prevention
@pytest.mark.asyncio
async def test_idor_prevent_unauthorized_resume_access(
    async_test_db, victim_resume, attacker_user
):
    with pytest.raises(ForbiddenError):
        await verify_resume_ownership(
            resume_id=victim_resume.id,
            current_user=attacker_user,
            db=async_test_db,
        )


@pytest.mark.asyncio
async def test_idor_prevent_unauthorized_analysis_access(
    async_test_db, victim_analysis, attacker_user
):
    with pytest.raises(ForbiddenError):
        await verify_analysis_ownership(
            analysis_id=victim_analysis.id,
            current_user=attacker_user,
            db=async_test_db,
        )


# 2. Path Traversal & Filename Sanitization
def test_path_traversal_sanitization():
    malicious_filenames = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "nested/../../secret.txt",
        "eval\x00_test.pdf",
        "../../../root/.ssh/id_rsa",
    ]

    for fname in malicious_filenames:
        sanitized = sanitize_filename(fname)
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert ".." not in sanitized
        assert "\x00" not in sanitized


# 3. HTTP Security Headers Compliance
@pytest.mark.asyncio
async def test_security_headers_present():
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        headers = resp.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "Strict-Transport-Security" in headers
        assert "X-Request-ID" in headers


# 4. SQL Injection Resistance
@pytest.mark.asyncio
async def test_sqli_attack_payload_handled_safely(async_test_db, attacker_user):
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT null, null, null--",
    ]

    for sqli in sqli_payloads:
        with pytest.raises((ForbiddenError, Exception)):
            await verify_analysis_ownership(
                analysis_id=sqli,
                current_user=attacker_user,
                db=async_test_db,
            )
