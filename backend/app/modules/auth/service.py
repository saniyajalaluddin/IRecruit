"""Authentication service for hashing, token generation, and signature verification."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from backend.app.core.config import get_settings
from backend.app.core.errors import UnauthorizedError
from backend.app.modules.auth.schemas import Token, TokenPayload

settings = get_settings()


class AuthService:
    """Handles password hashing, token creation, and JWT verification."""

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hashes a plaintext password using bcrypt with salt."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against a stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    @staticmethod
    def create_access_token(
        subject: str,
        email: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Generates a signed JWT access token."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": subject,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }
        encoded_jwt = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def create_token_pair(subject: str, email: Optional[str] = None) -> Token:
        """Creates an access token and refresh token bundle."""
        access_token = AuthService.create_access_token(subject=subject, email=email)
        now = datetime.now(timezone.utc)
        refresh_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_payload = {
            "sub": subject,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(refresh_expires.timestamp()),
            "type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
        )

    @staticmethod
    def decode_token(token: str) -> TokenPayload:
        """Decodes and validates a signed JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            sub = payload.get("sub")
            if not sub:
                raise UnauthorizedError("Token missing subject identifier")

            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            iat = datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc)
            return TokenPayload(
                sub=sub,
                email=payload.get("email"),
                is_active=payload.get("is_active", True),
                exp=exp,
                iat=iat,
            )
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Authentication token has expired")
        except (jwt.InvalidTokenError, Exception) as exc:
            raise UnauthorizedError("Invalid authentication credentials") from exc
