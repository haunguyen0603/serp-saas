import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_password, hash_refresh_token, verify_password
from app.models.password_reset import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserStatus
from app.services.auth_email import AuthEmailSender, PasswordResetEmail
from app.services.users import require_active

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingPasswordReset:
    email: PasswordResetEmail = field(repr=False)


class PasswordService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def request_reset(self, email: str) -> PendingPasswordReset | None:
        if self.settings.auth_email_provider == "disabled":
            raise AppError(
                503,
                "AUTH_EMAIL_UNAVAILABLE",
                "Email delivery is unavailable. Please try again later.",
            )
        user = await self.session.scalar(
            select(User)
            .where(User.email == email)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        # Identical response for unknown, disabled and throttled accounts.
        if user is None or user.status != UserStatus.ACTIVE:
            return None
        now = datetime.now(UTC)
        recent = (
            await self.session.scalars(
                select(PasswordResetToken.created_at)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.created_at > now - timedelta(hours=1),
                )
                .order_by(PasswordResetToken.created_at.desc())
            )
        ).all()
        if recent and (
            recent[0]
            + timedelta(seconds=self.settings.auth_password_reset_resend_seconds)
            > now
            or len(recent) >= self.settings.auth_password_reset_max_emails_per_hour
        ):
            return None
        await self.revoke_resets(user.id, now)
        raw = secrets.token_urlsafe(48)
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw),
                expires_at=now
                + timedelta(minutes=self.settings.auth_password_reset_expire_minutes),
                created_at=now,
            )
        )
        await self.session.flush()
        return PendingPasswordReset(
            PasswordResetEmail(
                user.email,
                f"{self.settings.auth_site_url}/reset-password#token={raw}",
                self.settings.auth_password_reset_expire_minutes,
            )
        )

    async def revoke_resets(self, user_id: UUID, now: datetime) -> None:
        await self.session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def replace_password(self, user: User, password: str) -> None:
        if await run_in_threadpool(verify_password, password, user.password_hash):
            raise AppError(
                400,
                "PASSWORD_UNCHANGED",
                "Choose a password different from your current password.",
            )
        user.password_hash = await run_in_threadpool(hash_password, password)
        user.password_version += 1
        now = datetime.now(UTC)
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.revoke_resets(user.id, now)
        await self.session.flush()

    async def reset(self, raw: str, password: str) -> None:
        token = await self.session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_refresh_token(raw)
            )
        )
        if token is None:
            raise AppError(
                400,
                "INVALID_PASSWORD_RESET_TOKEN",
                "This reset link is invalid or has already been used. "
                "Request a new link.",
            )
        # Every password mutation and resend locks the account first.
        user = await self.session.scalar(
            select(User)
            .where(User.id == token.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise AppError(
                400,
                "INVALID_PASSWORD_RESET_TOKEN",
                "This reset link is invalid or has already been used. "
                "Request a new link.",
            )
        require_active(user)
        await self.session.refresh(token, with_for_update=True)
        if token.used_at is not None or token.revoked_at is not None:
            raise AppError(
                400,
                "INVALID_PASSWORD_RESET_TOKEN",
                "This reset link is invalid or has already been used. "
                "Request a new link.",
            )
        if token.expires_at <= datetime.now(UTC):
            raise AppError(
                410,
                "PASSWORD_RESET_TOKEN_EXPIRED",
                "This reset link has expired. Request a new link.",
            )
        token.used_at = datetime.now(UTC)
        await self.replace_password(user, password)

    async def change(self, authenticated: User, current: str, password: str) -> User:
        version = authenticated.password_version
        user = await self.session.scalar(
            select(User)
            .where(User.id == authenticated.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None or user.password_version != version:
            raise AppError(401, "INVALID_ACCESS_TOKEN", "Please log in again.")
        require_active(user)
        if not await run_in_threadpool(verify_password, current, user.password_hash):
            raise AppError(
                400, "INVALID_CURRENT_PASSWORD", "Your current password is incorrect."
            )
        await self.replace_password(user, password)
        return user


async def deliver_password_reset_email(
    pending: PendingPasswordReset, sender: AuthEmailSender
) -> None:
    # Background tasks run only after the request transaction commits.
    try:
        await sender.send(pending.email)
    except Exception:
        logger.warning("Password reset email delivery failed")
