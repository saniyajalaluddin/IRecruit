"""Health check, readiness probes, and telemetry endpoints."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.modules.observability.metrics import telemetry
from backend.app.schemas.common import HealthResponse, StandardResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=StandardResponse[HealthResponse],
    summary="Application Health Status",
    description="Returns service health status, environment mode, database connectivity, and server timestamp.",
)
async def check_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[HealthResponse]:
    settings = get_settings()
    request_id = getattr(request.state, "request_id", "system")

    # Verify Database Connectivity
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    overall_status = "healthy" if db_status == "connected" else "degraded"

    return StandardResponse(
        success=True,
        data=HealthResponse(
            status=overall_status,
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            database=db_status,
            telemetry=telemetry.get_summary(),
        ),
        request_id=request_id,
    )


@router.get(
    "/health/telemetry",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Application Telemetry Metrics",
    description="Exposes in-memory request counts, error rates, and p50/p95/p99 latency percentiles.",
)
async def get_telemetry(request: Request) -> StandardResponse[Dict[str, Any]]:
    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=telemetry.get_summary(),
        request_id=request_id,
    )
