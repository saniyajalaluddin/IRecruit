"""User schemas and role specifications."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User privilege roles."""
    CANDIDATE = "candidate"
    ADMIN = "admin"


class UserBase(BaseModel):
    """Base user properties."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=100, description="User full name")


class UserCreate(UserBase):
    """Schema for registering a new user."""
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=100)
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserRead(UserBase):
    """Schema for public/authenticated user profile response."""
    id: str = Field(..., description="Unique user identifier")
    role: UserRole = Field(default=UserRole.CANDIDATE, description="Assigned role")
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True
