import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import AppError

_password_hasher = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: UUID, settings: Settings, password_version: int = 0
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "password_version": password_version,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str, settings: Settings, password_version: int | None = None
) -> UUID:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
        if claims["type"] != "access":
            raise ValueError("Wrong token type")
        if (
            password_version is not None
            and claims.get("password_version", 0) != password_version
        ):
            raise ValueError("Password changed")
        return UUID(claims["sub"])
    except jwt.ExpiredSignatureError:
        raise AppError(
            401, "EXPIRED_ACCESS_TOKEN", "Your session needs to be refreshed."
        ) from None
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise AppError(401, "INVALID_ACCESS_TOKEN", "Invalid access token.") from None


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
