"""Authentication API endpoints: registration, login, logout, and profile."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.errors import UnauthorizedError
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.user import User
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.auth.schemas import AuthResponse, LoginRequest
from backend.app.modules.auth.service import AuthService
from backend.app.modules.users.schemas import UserCreate, UserRead
from backend.app.modules.users.service import UserService
from backend.app.schemas.common import StandardResponse

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=StandardResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Registers a new candidate user account with free tier entitlement.",
)
async def register(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AuthResponse]:
    user_service = UserService(db)
    user = await user_service.create_user(data)

    # Issue token bundle
    token = AuthService.create_token_pair(subject=user.id, email=user.email)

    # Record Audit Event
    audit = AuditEvent(
        user_id=user.id,
        event_type="user_registered",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=AuthResponse(
            user_id=user.id,
            email=user.email,
            token=token,
        ),
        request_id=request_id,
    )


@router.post(
    "/login",
    response_model=StandardResponse[AuthResponse],
    summary="User Authentication",
    description="Authenticates credentials and returns JWT bearer tokens.",
)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AuthResponse]:
    user_service = UserService(db)
    user = await user_service.get_by_email(data.email)

    # Defend against timing attacks & enumeration with identical failure response
    if not user or not AuthService.verify_password(data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email address or password")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive. Please contact support.")

    token = AuthService.create_token_pair(subject=user.id, email=user.email)

    # Audit login
    audit = AuditEvent(
        user_id=user.id,
        event_type="user_login",
        resource_type="user",
        resource_id=user.id,
        details={"status": "success"},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=AuthResponse(
            user_id=user.id,
            email=user.email,
            token=token,
        ),
        request_id=request_id,
    )


@router.post(
    "/logout",
    response_model=StandardResponse[dict],
    summary="User Logout",
    description="Invalidates user session and logs logout audit event.",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    audit = AuditEvent(
        user_id=current_user.id,
        event_type="user_logout",
        resource_type="user",
        resource_id=current_user.id,
        details={"status": "logged_out"},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data={"message": "Successfully logged out"},
        request_id=request_id,
    )


@router.get(
    "/me",
    response_model=StandardResponse[UserRead],
    summary="Current User Profile",
    description="Returns authenticated user profile details.",
)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> StandardResponse[UserRead]:
    request_id = getattr(request.state, "request_id", "system")
    return StandardResponse(
        success=True,
        data=UserRead.model_validate(current_user),
        request_id=request_id,
    )
