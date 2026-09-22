"""User service interface and lifecycle management."""

from typing import Optional, Protocol
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.errors import ConflictError, NotFoundError
from backend.app.models.entitlement import Entitlement
from backend.app.models.user import User
from backend.app.modules.auth.service import AuthService
from backend.app.modules.users.schemas import UserCreate, UserUpdate


class UserServiceInterface(Protocol):
    """Protocol defining the user management service contract."""

    async def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    async def create_user(self, data: UserCreate) -> User:
        ...

    async def update_profile(self, user_id: str, data: UserUpdate) -> User:
        ...


class UserService:
    """Handles user persistence, profile retrieval, and account lifecycles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Fetch user ORM entity by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user ORM entity by email."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, data: UserCreate) -> User:
        """Creates and registers a new user with default free tier entitlement."""
        existing = await self.get_by_email(data.email)
        if existing:
            raise ConflictError("An account with this email address already exists.")

        hashed_pw = AuthService.hash_password(data.password)
        user = User(
            email=data.email.lower().strip(),
            hashed_password=hashed_pw,
            full_name=data.full_name,
            role="candidate",
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        # Provision default entitlement (Free tier with 5 saved analyses)
        entitlement = Entitlement(
            user_id=user.id,
            tier="free",
            max_saved_analyses=5,
            analyses_count=0,
            is_active=True,
        )
        self.db.add(entitlement)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_profile(self, user_id: str, data: UserUpdate) -> User:
        """Updates user profile details."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")

        if data.full_name is not None:
            user.full_name = data.full_name

        if data.new_password:
            if not data.current_password or not AuthService.verify_password(data.current_password, user.hashed_password):
                raise ConflictError("Current password verification failed.")
            user.hashed_password = AuthService.hash_password(data.new_password)

        await self.db.commit()
        await self.db.refresh(user)
        return user
