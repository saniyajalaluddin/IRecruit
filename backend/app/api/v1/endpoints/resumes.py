"""Resumes management API endpoints with secure upload and strict ownership enforcement."""

import io
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
import pypdf
import docx

from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user, get_optional_user_payload
from backend.app.modules.auth.schemas import TokenPayload
from backend.app.modules.documents import DocumentFormat, DocumentUploadService, TemporaryStorageManager
from backend.app.modules.privacy.service import PIIService
from backend.app.modules.security.authorization import verify_resume_ownership
from backend.app.schemas.common import StandardResponse

router = APIRouter(prefix="/resumes")


def _extract_initial_text(content: bytes, doc_format: DocumentFormat) -> str:
    """Extracts raw plaintext safely for initial resume version storage."""
    text = ""
    bio = io.BytesIO(content)
    if doc_format == DocumentFormat.TXT:
        text = content.decode("utf-8", errors="replace")
    elif doc_format == DocumentFormat.PDF:
        reader = pypdf.PdfReader(bio)
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text)
    elif doc_format == DocumentFormat.DOCX:
        doc = docx.Document(bio)
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paras)
    return text.strip()


@router.post(
    "/upload",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Secure Resume Upload",
    description="Uploads a PDF, DOCX, or TXT resume with MIME sniffing, size checks, and sanitization.",
)
async def upload_resume(
    request: Request,
    file: UploadFile = File(..., description="Resume document file"),
    title: Optional[str] = Form(None, description="Custom label/title for resume"),
    auth_payload: Optional[TokenPayload] = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    # 1. Process upload safely (size limits, magic bytes, integrity, sanitized storage)
    upload_service = DocumentUploadService()
    metadata, content_bytes = await upload_service.process_and_store_upload(file)

    # 2. Extract initial plaintext and generate PII-masked version
    raw_text = _extract_initial_text(content_bytes, metadata.format)
    redaction = PIIService.redact_pii(raw_text)

    # 3. Associate with user if authenticated, otherwise mark anonymous
    user_id = auth_payload.sub if auth_payload else None
    is_anonymous = user_id is None

    resume = Resume(
        user_id=user_id,
        title=title or metadata.sanitized_filename,
        original_filename=metadata.original_filename,
        file_path=metadata.storage_path or "",
        file_size_bytes=metadata.file_size_bytes,
        content_type=metadata.content_type,
        is_anonymous=is_anonymous,
    )
    db.add(resume)
    await db.flush()

    # Initial version record
    version = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        raw_text=raw_text,
        pii_masked_text=redaction.sanitized_text,
        structured_data={},
    )
    db.add(version)

    # Audit logging
    audit = AuditEvent(
        user_id=user_id,
        event_type="resume_uploaded",
        resource_type="resume",
        resource_id=resume.id,
        details={
            "format": metadata.format.value,
            "size_bytes": str(metadata.file_size_bytes),
            "is_anonymous": str(is_anonymous),
        },
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data={
            "resume_id": resume.id,
            "version_id": version.id,
            "title": resume.title,
            "original_filename": resume.original_filename,
            "format": metadata.format.value,
            "file_size_bytes": resume.file_size_bytes,
            "is_anonymous": is_anonymous,
        },
        request_id=request_id,
    )


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
