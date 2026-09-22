"""Resumes management API endpoints with strict ownership enforcement."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.documents.storage import TemporaryStorageManager
from backend.app.modules.security.authorization import verify_resume_ownership
from backend.app.schemas.common import StandardResponse

router = APIRouter(prefix="/resumes")


@router.get(
    "/{resume_id}",
    response_model=StandardResponse[dict],
    summary="Get Resume Metadata",
    description="Fetches resume metadata strictly verifying candidate ownership.",
)
async def get_resume(
    resume_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    resume = await verify_resume_ownership(resume_id, current_user, db)
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data={
            "id": resume.id,
            "title": resume.title,
            "original_filename": resume.original_filename,
            "file_size_bytes": resume.file_size_bytes,
            "content_type": resume.content_type,
            "created_at": resume.created_at.isoformat(),
        },
        request_id=request_id,
    )


@router.delete(
    "/{resume_id}",
    response_model=StandardResponse[dict],
    summary="Delete Resume",
    description="Permanently deletes resume and associated data strictly verifying ownership.",
)
async def delete_resume(
    resume_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    resume = await verify_resume_ownership(resume_id, current_user, db)

    # Clean up file on disk if path exists
    TemporaryStorageManager.cleanup_file(resume.file_path)

    await db.delete(resume)

    audit = AuditEvent(
        user_id=current_user.id,
        event_type="resume_deleted",
        resource_type="resume",
        resource_id=resume_id,
        details={"filename": resume.original_filename},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data={"message": "Resume successfully deleted"},
        request_id=request_id,
    )
