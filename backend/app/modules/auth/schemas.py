"""Authentication schemas and token models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Access and refresh token pair."""

    access_token: str = Field(..., description="Bearer access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token lifespan in seconds")
    refresh_token: Optional[str] = Field(default=None, description="Optional refresh token")


class TokenPayload(BaseModel):
    """Decoded JWT payload structure."""

    sub: str = Field(..., description="Subject identifier (user_id)")
    email: Optional[str] = Field(default=None, description="User email")
    is_active: bool = Field(default=True, description="Account active status")
    exp: datetime = Field(..., description="Token expiration timestamp")
    iat: datetime = Field(..., description="Issued at timestamp")


class LoginRequest(BaseModel):
    """User login request schema."""

    email: EmailStr = Field(..., description="Candidate user email")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")


class AuthResponse(BaseModel):
    """Standardized authentication response schema."""

    user_id: str
    email: str
    token: Token
