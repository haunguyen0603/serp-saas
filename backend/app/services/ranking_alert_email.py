"""Optional email outbox. SMTP is at-least-once across send/commit crashes."""

import html
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models.keyword import Keyword
from app.models.project import ProjectStatus
from app.models.ranking_alert import RankingAlert, RankingAlertDelivery
from app.models.tracked_site import TrackedSite, TrackedSiteStatus
from app.models.user import User, UserStatus
from app.repositories.ranking_alert import RankingAlertRepository
from app.services.auth_email import AuthEmailError, send_smtp_email
from app.services.ranking_alerts import TYPE_FLAGS

logger = logging.getLogger(__name__)
LABELS = {
    "entered_top10": "Entered Top 10",
    "left_top10": "Left Top 10",
    "rank_improved": "Improved",
    "rank_declined": "Declined",
}


def rank_label(position: int | None) -> str:
    return f"#{position}" if position is not None else "Not found in Top 10"


@dataclass(frozen=True)
class RankingAlertEmail:
    recipient: str = field(repr=False)
    subject: str
    body: str
    html_body: str
    message_id: str


class RankingAlertEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.messages: list[RankingAlertEmail] = []

    async def send(self, message: RankingAlertEmail) -> str:
        if self.settings.auth_email_provider == "fake":
            self.messages.append(message)
            return message.message_id
        if self.settings.auth_email_provider != "smtp":
            raise AuthEmailError("ALERT_EMAIL_UNAVAILABLE", transient=False)
        email = EmailMessage()
        email["From"] = self.settings.auth_email_from
        email["To"] = message.recipient
        email["Subject"] = message.subject
        email["Message-ID"] = message.message_id
        email.set_content(message.body)
        email.add_alternative(message.html_body, subtype="html")
        await send_smtp_email(self.settings, email)
        return message.message_id


class AlertEmailWorker:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        sender: RankingAlertEmailSender | None = None,
    ) -> None:
        self.factory, self.settings = factory, settings
        self.sender = sender or RankingAlertEmailSender(settings)

    async def deliver(self, delivery_id: UUID) -> bool:
        now = datetime.now(UTC)
        token = uuid4()
        async with self.factory() as session, session.begin():
            delivery = await session.scalar(
                select(RankingAlertDelivery)
                .where(
                    RankingAlertDelivery.id == delivery_id,
                )
                .with_for_update(skip_locked=True)
            )
            if delivery is None or delivery.status not in ("pending", "sending"):
                return False
            if (
                delivery.status == "sending"
                and delivery.lease_expires_at
                and delivery.lease_expires_at > now
            ):
                return False
            if delivery.next_attempt_at > now:
                return False
            if delivery.attempts >= 5:
                delivery.status, delivery.last_error = (
                    "failed",
                    "ALERT_EMAIL_RETRY_EXHAUSTED",
                )
                return True
            alert = await session.get(RankingAlert, delivery.alert_id)
            assert alert is not None
            # Serialize the cross-project per-user send cap.
            user = await session.get(User, alert.user_id, with_for_update=True)
            repo = RankingAlertRepository(session)
            project = await repo.project(alert.project_id, alert.user_id, lock=True)
            preferences = await repo.preferences(alert.project_id, alert.user_id)
            keyword = await session.get(Keyword, alert.keyword_id)
            site = (
                await session.get(TrackedSite, alert.tracked_site_id)
                if alert.tracked_site_id
                else None
            )
            if (
                not self.settings.ranking_alert_email_enabled
                or self.settings.auth_email_provider == "disabled"
                or not user
                or user.status != UserStatus.ACTIVE
                or not user.email_verified_at
                or not preferences.enabled
                or not preferences.email_enabled
                or not getattr(preferences, TYPE_FLAGS[alert.alert_type])
                or project.status != ProjectStatus.ACTIVE
                or not keyword
                or not keyword.active
                or not site
                or site.status != TrackedSiteStatus.ACTIVE
            ):
                delivery.status, delivery.last_error = (
                    "suppressed",
                    "ALERT_EMAIL_DISABLED_OR_INELIGIBLE",
                )
                return True
            attempts = int(
                await session.scalar(
                    select(func.coalesce(func.sum(RankingAlertDelivery.attempts), 0))
                    .join(
                        RankingAlert, RankingAlert.id == RankingAlertDelivery.alert_id
                    )
                    .where(
                        RankingAlert.user_id == user.id,
                        RankingAlertDelivery.last_attempt_at
                        >= now - timedelta(hours=1),
                    )
                )
                or 0
            )
            if attempts >= self.settings.ranking_alert_email_hourly_cap:
                delivery.next_attempt_at = now + timedelta(hours=1)
                delivery.last_error = "ALERT_EMAIL_THROTTLED"
                return False
            delivery.status, delivery.lease_token = "sending", token
            delivery.attempts += 1
            delivery.last_attempt_at = now
            delivery.lease_expires_at = now + timedelta(seconds=300)
            lines = [
                f"{LABELS[alert.alert_type]}: {alert.keyword}",
                f"Project: {alert.project_name} ({alert.device})",
                f"Site: {alert.site_name}",
                f"{rank_label(alert.previous_rank)} → {rank_label(alert.current_rank)}",
                f"Observed: {alert.observed_at.isoformat()} (UTC)",
                f"{self.settings.auth_site_url.rstrip('/')}/app/ranking-alerts",
            ]
            message = RankingAlertEmail(
                recipient=user.email,
                subject="SERP SaaS ranking alert: "
                + alert.keyword.replace("\r", " ").replace("\n", " ")[:150],
                body="\n".join(lines),
                html_body="<p>"
                + "<br>".join(html.escape(line) for line in lines)
                + "</p>",
                message_id=f"<ranking-alert-{delivery.id}@serpsaas.com>",
            )
            attempt = delivery.attempts
        error: AuthEmailError | None = None
        provider_id = None
        try:
            provider_id = await self.sender.send(message)
        except AuthEmailError as exc:
            error = exc
        except Exception:
            error = AuthEmailError("ALERT_EMAIL_FAILED")
        async with self.factory() as session, session.begin():
            stored = await session.get(
                RankingAlertDelivery, delivery_id, with_for_update=True
            )
            if stored is None or stored.lease_token != token:
                return False
            stored.lease_expires_at, stored.lease_token = None, None
            if error:
                stored.status = (
                    "pending" if error.transient and attempt < 5 else "failed"
                )
                stored.last_error = (
                    "ALERT_EMAIL_TRANSIENT_FAILURE"
                    if error.transient
                    else "ALERT_EMAIL_PERMANENT_FAILURE"
                )
                stored.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=min(3600, 30 * 2**attempt)
                )
            else:
                stored.status, stored.sent_at, stored.provider_message_id = (
                    "sent",
                    datetime.now(UTC),
                    provider_id,
                )
                stored.last_error = None
            logger.info(
                "ranking_alert_email_result",
                extra={
                    "delivery_id": str(delivery_id),
                    "delivery_status": stored.status,
                    "attempts": attempt,
                },
            )
        return True

    async def drain(self, limit: int = 50) -> int:
        now = datetime.now(UTC)
        async with self.factory() as session:
            ids = list(
                await session.scalars(
                    select(RankingAlertDelivery.id)
                    .where(
                        (
                            (RankingAlertDelivery.status == "pending")
                            & (RankingAlertDelivery.next_attempt_at <= now)
                        )
                        | (
                            (RankingAlertDelivery.status == "sending")
                            & (RankingAlertDelivery.lease_expires_at <= now)
                        )
                    )
                    .order_by(RankingAlertDelivery.next_attempt_at)
                    .limit(limit)
                )
            )
        count = 0
        for delivery_id in ids:
            try:
                count += await self.deliver(delivery_id)
            except Exception:
                logger.warning(
                    "ranking_alert_email_worker_failed",
                    extra={"delivery_id": str(delivery_id)},
                )
        return count
