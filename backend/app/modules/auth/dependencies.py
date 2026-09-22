"""Authentication dependencies and request bearer extractors."""

from typing import Optional
from fastapi import Depends, Header
from backend.app.core.errors import UnauthorizedError
from backend.app.modules.auth.schemas import TokenPayload
from backend.app.modules.auth.service import AuthService


async def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extracts raw Bearer token from the Authorization header."""
    if not authorization:
        raise UnauthorizedError("Authorization header is missing")

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must follow 'Bearer <token>' format")

    return parts[1]


async def get_current_user_payload(token: str = Depends(get_token_from_header)) -> TokenPayload:
    """Validates the bearer token and returns the current user payload."""
    return AuthService.decode_token(token)


async def get_optional_user_payload(authorization: Optional[str] = Header(None)) -> Optional[TokenPayload]:
    """Extracts user payload if authorization header is provided, otherwise returns None for anonymous access."""
    if not authorization:
        return None
    try:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return AuthService.decode_token(parts[1])
    except Exception:
        pass
    return None
