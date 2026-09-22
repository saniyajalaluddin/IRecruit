"""Health check and service status endpoints."""

from fastapi import APIRouter, Request
from backend.app.core.config import get_settings
from backend.app.schemas.common import HealthResponse, StandardResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=StandardResponse[HealthResponse],
    summary="Application Health Status",
    description="Returns service health status, environment mode, and server timestamp.",
)
async def check_health(request: Request) -> StandardResponse[HealthResponse]:
    settings = get_settings()
    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=HealthResponse(
            status="healthy",
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        ),
        request_id=request_id,
    )
