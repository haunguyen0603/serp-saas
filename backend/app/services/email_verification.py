import logging
import math
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_refresh_token
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.schemas.email_verification import VerificationStatus
from app.services.auth_email import AuthEmailSender, VerificationEmail
from app.services.users import require_active

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingVerification:
    token_id: UUID
    email: VerificationEmail = field(repr=False)


class EmailVerificationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def latest(self, user_id: UUID) -> EmailVerificationToken | None:
        return cast(
            EmailVerificationToken | None,
            await self.session.scalar(
                select(EmailVerificationToken)
                .where(EmailVerificationToken.user_id == user_id)
                .order_by(
                    EmailVerificationToken.created_at.desc(),
                    EmailVerificationToken.id.desc(),
                )
                .limit(1)
            ),
        )

    async def status(self, user: User) -> VerificationStatus:
        if user.email_verified_at is not None:
            return VerificationStatus(
                verified=True, delivery_status="verified", retry_after_seconds=0
            )
        token = await self.latest(user.id)
        now = datetime.now(UTC)
        retry = 0
        if token:
            retry = max(
                0,
                math.ceil(
                    (
                        token.created_at
                        + timedelta(
                            seconds=self.settings.auth_verification_resend_seconds
                        )
                        - now
                    ).total_seconds()
                ),
            )
            recent = (
                await self.session.scalars(
                    select(EmailVerificationToken.created_at)
                    .where(
                        EmailVerificationToken.user_id == user.id,
                        EmailVerificationToken.created_at > now - timedelta(hours=1),
                    )
                    .order_by(EmailVerificationToken.created_at)
                )
            ).all()
            if len(recent) >= self.settings.auth_verification_max_emails_per_hour:
                retry = max(
                    retry,
                    math.ceil((recent[0] + timedelta(hours=1) - now).total_seconds()),
                )
        return VerificationStatus(
            verified=False,
            delivery_status=token.delivery_status if token else "not_requested",
            retry_after_seconds=retry,
            expires_at=token.expires_at if token else None,
        )

    async def request(self, user_id: UUID) -> PendingVerification | None:
        # Serialize resends and verification on the same account, across API instances.
        user = await self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise AppError(401, "INVALID_ACCESS_TOKEN", "Invalid access token.")
        require_active(user)
        if user.email_verified_at is not None:
            return None
        if self.settings.auth_email_provider == "disabled":
            raise AppError(
                503,
                "AUTH_EMAIL_UNAVAILABLE",
                "Email delivery is unavailable. Please try again later.",
            )
        state = await self.status(user)
        if state.retry_after_seconds:
            raise AppError(
                429,
                "VERIFICATION_RATE_LIMITED",
                "Please wait before requesting another email.",
                details={"retry_after_seconds": state.retry_after_seconds},
            )
        now = datetime.now(UTC)
        await self.session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        raw = secrets.token_urlsafe(48)
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw),
            expires_at=now
            + timedelta(minutes=self.settings.auth_verification_expire_minutes),
            created_at=now,
        )
        self.session.add(token)
        await self.session.flush()
        return PendingVerification(
            token.id,
            VerificationEmail(
                user.email,
                f"{self.settings.auth_site_url}/verify-email#token={raw}",
                self.settings.auth_verification_expire_minutes,
            ),
        )

    async def verify(self, raw: str) -> User:
        token = await self.session.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == hash_refresh_token(raw)
            )
        )
        if token is None:
            raise AppError(
                400,
                "INVALID_VERIFICATION_TOKEN",
                "This verification link is invalid or has already been used.",
            )
        user = await self.session.scalar(
            select(User)
            .where(User.id == token.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise AppError(
                400,
                "INVALID_VERIFICATION_TOKEN",
                "This verification link is invalid or has already been used.",
            )
        require_active(user)
        # Refresh the token after acquiring the account lock: a concurrent resend
        # or confirmation may have invalidated the initially read record.
        await self.session.refresh(token, with_for_update=True)
        now = datetime.now(UTC)
        if (
            token.used_at is not None
            or token.revoked_at is not None
            or user.email_verified_at is not None
        ):
            raise AppError(
                400,
                "INVALID_VERIFICATION_TOKEN",
                "This verification link is invalid or has already been used.",
            )
        if token.expires_at <= now:
            raise AppError(
                410,
                "VERIFICATION_TOKEN_EXPIRED",
                "This verification link has expired. Request a new email.",
            )
        user.email_verified_at = now
        token.used_at = now
        await self.session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.revoked_at.is_(None),
                EmailVerificationToken.id != token.id,
            )
            .values(revoked_at=now)
        )
        await self.session.flush()
        return user


async def deliver_verification_email(
    pending: PendingVerification,
    sender: AuthEmailSender,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    # Called as an HTTP background task, after the request's transaction commits.
    # Only the hash is persisted; an interrupted delivery can be retried by resend.
    outcome = "sent"
    try:
        await sender.send(pending.email)
    except Exception:
        outcome = "failed"
        logger.warning("Verification email delivery failed")
    try:
        async with factory.begin() as session:
            await session.execute(
                update(EmailVerificationToken)
                .where(EmailVerificationToken.id == pending.token_id)
                .values(delivery_status=outcome)
            )
    except Exception:
        logger.warning("Verification email delivery status could not be saved")
