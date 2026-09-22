"""Job Description API endpoints: parsing, requirement extraction, and persistence."""

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.errors import ValidationError
from backend.app.db.session import get_db
from backend.app.models.job_description import JobDescription
from backend.app.modules.auth.dependencies import get_optional_user_payload
from backend.app.modules.auth.schemas import TokenPayload
from backend.app.modules.job_descriptions.schemas import ParsedJobDescription
from backend.app.modules.job_descriptions.service import JobDescriptionService
from backend.app.modules.security.prompt_defense import PromptInjectionDetector
from backend.app.schemas.common import StandardResponse

router = APIRouter(prefix="/job-descriptions")


class ParseJDRequest(BaseModel):
    """Payload for submitting a Job Description."""
    raw_text: str = Field(..., min_length=20, description="Pasted raw job description text")
    title: str | None = Field(None, description="Optional job title")
    company_name: str | None = Field(None, description="Optional company name")


@router.post(
    "/parse",
    response_model=StandardResponse[ParsedJobDescription],
    status_code=status.HTTP_200_OK,
    summary="Parse Job Description",
    description="Extracts prioritized requirements, categories, and technologies strictly based on JD text.",
)
async def parse_job_description(
    payload: ParseJDRequest,
    request: Request,
    auth_payload: TokenPayload | None = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[ParsedJobDescription]:
    # 1. Sanitize untrusted user input against prompt injection
    sanitized_text = PromptInjectionDetector.sanitize_untrusted_input(payload.raw_text)

    # 2. Parse JD
    service = JobDescriptionService()
    parsed_jd = await service.parse(sanitized_text)

    # 3. If user provided custom title/company, override inferred values
    if payload.title:
        parsed_jd.job_title = payload.title
    if payload.company_name:
        parsed_jd.company_name = payload.company_name

    # 4. Optionally persist in database
    user_id = auth_payload.sub if auth_payload else None
    jd_record = JobDescription(
        user_id=user_id,
        title=parsed_jd.job_title,
        company_name=parsed_jd.company_name,
        raw_text=sanitized_text,
        structured_requirements={"requirements": [r.model_dump() for r in parsed_jd.requirements]},
    )
    db.add(jd_record)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=parsed_jd,
        request_id=request_id,
    )
