"""Application-wide domain error classes and standard exception handlers."""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.logging import logger


class AppException(Exception):
    """Base application exception with status code and error code."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str = "Requested resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            details=details,
        )


class UnauthorizedError(AppException):
    """Authentication required or credentials invalid."""

    def __init__(self, message: str = "Authentication credentials invalid or missing", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenError(AppException):
    """Resource access forbidden / ownership violation."""

    def __init__(self, message: str = "You do not have permission to access this resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN_RESOURCE_ACCESS",
            details=details,
        )


class ValidationError(AppException):
    """Business rule or input validation error."""

    def __init__(self, message: str = "Invalid input or business rule constraint violated", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(AppException):
    """Resource conflict, e.g. duplicate email."""

    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code="RESOURCE_CONFLICT",
            details=details,
        )


class RateLimitExceededError(AppException):
    """Rate limit or quota exceeded."""

    def __init__(self, message: str = "Rate limit exceeded. Please retry later.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class AIProviderError(AppException):
    """AI Provider failure or timeout."""

    def __init__(self, message: str = "AI inference service temporarily unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="AI_PROVIDER_ERROR",
            details=details,
        )


class UnsupportedDocumentError(AppException):
    """Uploaded document format is invalid or unsupported."""

    def __init__(self, message: str = "Unsupported or malformed document", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="UNSUPPORTED_DOCUMENT",
            details=details,
        )


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str = "unknown",
    details: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Constructs a deterministic JSON error response envelope."""
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "request_id": request_id,
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles domain AppExceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"Domain error: {exc.code} - {exc.message}",
        extra={"request_id": request_id},
    )
    headers = {}
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS and exc.details and "retry_after_seconds" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after_seconds"])

    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
        headers=headers or None,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI/Pydantic request validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    errors = exc.errors()
    # Strip sensitive details from validation errors
    clean_errors = [
        {
            "loc": [str(loc) for loc in err.get("loc", [])],
            "msg": err.get("msg"),
            "type": err.get("type"),
        }
        for err in errors
    ]
    logger.info(
        f"Validation failure on {request.url.path}",
        extra={"request_id": request_id},
    )
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="REQUEST_VALIDATION_FAILED",
        message="The submitted request body or parameters are invalid.",
        request_id=request_id,
        details={"validation_errors": clean_errors},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard Starlette/FastAPI HTTPExceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    return build_error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        request_id=request_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled server errors, logging safely without exposing internals."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled server exception: {exc.__class__.__name__}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        request_id=request_id,
    )
