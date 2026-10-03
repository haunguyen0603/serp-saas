import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services.email_verification import (
    EmailVerificationService,
    PendingVerification,
)
from app.services.users import require_active

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IssuedSession:
    response: AuthResponse = field(repr=False)
    refresh_token: str = field(repr=False)
    verification: PendingVerification | None = field(default=None, repr=False)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        settings: Settings,
        dummy_password_hash: str,
    ) -> None:
        self.users = users
        self.tokens = tokens
        self.settings = settings
        self.dummy_password_hash = dummy_password_hash

    async def issue_session(self, user: User) -> IssuedSession:
        raw = generate_refresh_token()
        await self.tokens.create(
            user.id,
            hash_refresh_token(raw),
            datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
        )
        return IssuedSession(
            AuthResponse(
                access_token=create_access_token(user.id, self.settings),
                expires_in=self.settings.access_token_expire_minutes * 60,
                user=UserResponse.from_user(user),
                email_verification_required=self.settings.auth_require_verified_email,
            ),
            raw,
        )

    async def register(self, data: RegisterRequest) -> IssuedSession:
        password_hash = await run_in_threadpool(
            hash_password, data.password.get_secret_value()
        )
        user = await self.users.create(
            str(data.email), password_hash, datetime.now(UTC)
        )
        if user is None:
            raise AppError(
                409, "EMAIL_ALREADY_REGISTERED", "This email is already registered."
            )
        pending = await EmailVerificationService(
            self.users.session, self.settings
        ).request(user.id)
        issued = await self.issue_session(user)
        result = IssuedSession(issued.response, issued.refresh_token, pending)
        logger.info("Registration succeeded")
        return result

    async def login(self, data: LoginRequest) -> IssuedSession:
        user = await self.users.get_by_email(str(data.email))
        valid = await run_in_threadpool(
            verify_password,
            data.password.get_secret_value(),
            user.password_hash if user else self.dummy_password_hash,
        )
        if user is None or not valid:
            logger.info("Login failed")
            raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
        require_active(user)
        await self.users.record_login(user)
        result = await self.issue_session(user)
        logger.info("Login succeeded")
        return result

    async def refresh(self, raw: str | None) -> IssuedSession:
        if raw is None or len(raw) > 256:
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh session.")
        token = await self.tokens.get_by_hash_for_update(hash_refresh_token(raw))
        now = datetime.now(UTC)
        if token is None or token.revoked_at is not None or token.expires_at <= now:
            logger.info("Refresh rejected")
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh session.")
        user = await self.users.get_by_id(token.user_id)
        if user is None:
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh session.")
        require_active(user)
        await self.tokens.revoke(token, now, used=True)
        result = await self.issue_session(user)
        logger.info("Refresh succeeded")
        return result

    async def logout(self, raw: str | None) -> None:
        if raw is not None and len(raw) <= 256:
            token = await self.tokens.get_by_hash_for_update(hash_refresh_token(raw))
            if token is not None:
                await self.tokens.revoke(token, datetime.now(UTC))
        logger.info("Logout")
