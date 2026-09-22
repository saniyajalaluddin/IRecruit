"""Analyses management API endpoints with ownership enforcement, anonymous analysis, and claiming."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rate_limit import RateLimiter
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.user import User
from backend.app.modules.analysis.schemas import (
    AnonymousAnalysisRequest,
    AnonymousAnalysisResponse,
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
)
from backend.app.modules.analysis.service import anonymous_analysis_service
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.dashboard.schemas import AnalysisHistoryResponse, DashboardMetrics
from backend.app.modules.dashboard.service import dashboard_service
from backend.app.modules.security.authorization import verify_analysis_ownership
from backend.app.schemas.common import StandardResponse

router = APIRouter(prefix="/analyses")

anonymous_rate_limiter = RateLimiter(tier="anonymous_analysis")


@router.post(
    "/anonymous",
    response_model=StandardResponse[AnonymousAnalysisResponse],
    summary="Run Anonymous Quick Analysis",
    description="Performs instant resume alignment and ATS parsing analysis without requiring an account.",
)
async def run_anonymous_analysis(
    request: Request,
    response: Response,
    payload: AnonymousAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AnonymousAnalysisResponse]:
    anonymous_rate_limiter(request, response)
    client_ip = request.client.host if request.client else None

    result = await anonymous_analysis_service.run_anonymous_analysis(
        db=db,
        request=payload,
        client_ip=client_ip,
    )
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data=result,
        request_id=request_id,
    )


@router.post(
    "/{analysis_id}/claim",
    response_model=StandardResponse[ClaimAnalysisResponse],
    summary="Claim Anonymous Analysis",
    description="Transfers an anonymous analysis to an authenticated candidate account using its session token.",
)
async def claim_analysis(
    analysis_id: str,
    request: Request,
    payload: ClaimAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[ClaimAnalysisResponse]:
    client_ip = request.client.host if request.client else None
    result = await anonymous_analysis_service.claim_analysis(
        db=db,
        analysis_id=analysis_id,
        session_id=payload.session_id,
        user=current_user,
        client_ip=client_ip,
    )
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data=result,
        request_id=request_id,
    )


@router.get(
    "/history",
    response_model=StandardResponse[AnalysisHistoryResponse],
    summary="Get User Analysis History",
    description="Retrieves the candidate's latest saved analyses respecting tier limits (up to 5 for free users).",
)
async def get_history(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AnalysisHistoryResponse]:
    history = await dashboard_service.get_analysis_history(db=db, user_id=current_user.id)
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data=history,
        request_id=request_id,
    )


@router.get(
    "/dashboard",
    response_model=StandardResponse[DashboardMetrics],
    summary="Get User Dashboard Metrics",
    description="Retrieves aggregated analysis metrics, average alignment score, and top missing skill gaps.",
)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[DashboardMetrics]:
    metrics = await dashboard_service.get_dashboard_metrics(db=db, user_id=current_user.id)
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data=metrics,
        request_id=request_id,
    )


@router.get(
    "/{analysis_id}",
    response_model=StandardResponse[dict],
    summary="Get Analysis Report",
    description="Fetches an analysis report strictly verifying candidate ownership.",
)
async def get_analysis(
    analysis_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    analysis = await verify_analysis_ownership(analysis_id, current_user, db)
    request_id = getattr(request.state, "request_id", "system")

    return StandardResponse(
        success=True,
        data={
            "id": analysis.id,
            "overall_score": analysis.overall_score,
            "component_scores": analysis.component_scores,
            "weights": analysis.weights,
            "scoring_version": analysis.scoring_version,
            "llm_provider": analysis.llm_provider,
            "llm_model": analysis.llm_model,
            "embedding_provider": analysis.embedding_provider,
            "embedding_model": analysis.embedding_model,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
        },
        request_id=request_id,
    )


@router.delete(
    "/{analysis_id}",
    response_model=StandardResponse[dict],
    summary="Delete Analysis",
    description="Permanently deletes an analysis and associated evidence strictly verifying ownership.",
)
async def delete_analysis(
    analysis_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    analysis = await verify_analysis_ownership(analysis_id, current_user, db)

    await db.delete(analysis)

    audit = AuditEvent(
        user_id=current_user.id,
        event_type="analysis_deleted",
        resource_type="analysis",
        resource_id=analysis_id,
        details={"score": str(analysis.overall_score)},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data={"message": "Analysis successfully deleted"},
        request_id=request_id,
    )
