"""User service interface and lifecycle management."""

from typing import Optional, Protocol
from backend.app.modules.users.schemas import UserCreate, UserRead, UserUpdate


class UserServiceInterface(Protocol):
    """Protocol defining the user management service contract."""

    async def get_by_id(self, user_id: str) -> Optional[UserRead]:
        """Fetch user by ID."""
        ...

    async def get_by_email(self, email: str) -> Optional[UserRead]:
        """Fetch user by email."""
        ...

    async def create_user(self, data: UserCreate) -> UserRead:
        """Register and persist a new candidate user."""
        ...

    async def update_user(self, user_id: str, data: UserUpdate) -> UserRead:
        """Update existing candidate profile."""
        ...

    async def delete_user(self, user_id: str) -> bool:
        """Completely delete candidate profile and associated data."""
        ...
