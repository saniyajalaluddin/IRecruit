"""Common standardized schemas and response envelopes."""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Structured error payload schema."""

    code: str = Field(..., description="Unique error code for client handling")
    message: str = Field(..., description="Human-readable safe error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary contextual details")


class StandardResponse(BaseModel, Generic[DataT]):
    """Standard unified response envelope for all API endpoints."""

    success: bool = Field(default=True, description="Operation success flag")
    data: Optional[DataT] = Field(default=None, description="Response payload")
    error: Optional[ErrorDetail] = Field(default=None, description="Error details if unsuccessful")
    request_id: str = Field(..., description="Traceability request identifier")


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str = Field(default="healthy", description="Application status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    database: str = Field(default="connected", description="Database connectivity status")
    telemetry: Optional[Dict[str, Any]] = Field(default=None, description="System telemetry overview")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current server timestamp in UTC",
    )
