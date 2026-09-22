"""Strict authorization and resource ownership verification."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.errors import ForbiddenError, NotFoundError
from backend.app.models.analysis import Analysis
from backend.app.models.job_description import JobDescription
from backend.app.models.resume import Resume
from backend.app.models.user import User


def verify_ownership(resource_owner_id: str | None, current_user_id: str, resource_name: str = "Resource") -> None:
    """Enforces that a resource can only be viewed, updated, or deleted by its verified owner."""
    if resource_owner_id != current_user_id:
        raise ForbiddenError(f"Access denied. You do not have permission to access this {resource_name.lower()}.")


async def verify_resume_ownership(resume_id: str, current_user: User, db: AsyncSession) -> Resume:
    """Retrieves resume and verifies that the current user is the owner."""
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if not resume:
        raise NotFoundError("Requested resume not found.")

    verify_ownership(resume.user_id, current_user.id, resource_name="Resume")
    return resume


async def verify_analysis_ownership(analysis_id: str, current_user: User, db: AsyncSession) -> Analysis:
    """Retrieves analysis and verifies that the current user is the owner."""
    stmt = select(Analysis).where(Analysis.id == analysis_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise NotFoundError("Requested analysis not found.")

    verify_ownership(analysis.user_id, current_user.id, resource_name="Analysis")
    return analysis


async def verify_job_description_ownership(jd_id: str, current_user: User, db: AsyncSession) -> JobDescription:
    """Retrieves job description and verifies that the current user is the owner."""
    stmt = select(JobDescription).where(JobDescription.id == jd_id)
    result = await db.execute(stmt)
    jd = result.scalar_one_or_none()

    if not jd:
        raise NotFoundError("Requested job description not found.")

    verify_ownership(jd.user_id, current_user.id, resource_name="JobDescription")
    return jd
