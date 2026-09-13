from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import UsageEvent, UsagePeriod, UsageReservation
from app.models.rank_job import RankCheckJob
from app.services.billing.subscriptions import SubscriptionService


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.subscriptions = SubscriptionService(session)

    async def reserve(self, user_id: UUID, device: str, amount: int) -> UsagePeriod:
        if amount <= 0:
            raise AppError(422, "VALIDATION_ERROR", "Reservation must be positive.")
        sub = await self.subscriptions.resolve(user_id, device)
        period = await self.subscriptions.period(sub)
        result = await self.session.execute(
            update(UsagePeriod)
            .where(
                UsagePeriod.id == period.id,
                UsagePeriod.keyword_check_limit
                + UsagePeriod.adjustment
                - UsagePeriod.committed_keyword_checks
                - UsagePeriod.reserved_keyword_checks
                >= amount,
            )
            .values(
                reserved_keyword_checks=UsagePeriod.reserved_keyword_checks + amount
            )
            .returning(UsagePeriod.id)
        )
        if result.scalar_one_or_none() is None:
            await self.session.refresh(period)
            remaining = max(
                0,
                period.keyword_check_limit
                + period.adjustment
                - period.committed_keyword_checks
                - period.reserved_keyword_checks,
            )
            raise AppError(
                409,
                "USAGE_LIMIT_EXCEEDED",
                f"Monthly checks exhausted: {remaining} remaining, {amount} requested.",
                details={
                    "limit": period.keyword_check_limit + period.adjustment,
                    "used": period.committed_keyword_checks,
                    "reserved": period.reserved_keyword_checks,
                    "remaining": remaining,
                    "requested": amount,
                },
            )
        return period

    def attach(self, period: UsagePeriod, jobs: list[RankCheckJob]) -> None:
        self.session.add_all(
            [
                UsageReservation(
                    usage_period_id=period.id,
                    user_id=period.user_id,
                    device_scope=period.device_scope,
                    batch_id=job.batch_id,
                    job_id=job.id,
                )
                for job in jobs
            ]
        )

    async def settle(self, job_id: UUID, commit: bool) -> bool:
        reservation = await self.session.scalar(
            select(UsageReservation)
            .where(UsageReservation.job_id == job_id)
            .with_for_update()
        )
        if reservation is None:
            return False
        if reservation.status != "reserved":
            return reservation.status == "committed"
        values = {"reserved_keyword_checks": UsagePeriod.reserved_keyword_checks - 1}
        if commit:
            values["committed_keyword_checks"] = (
                UsagePeriod.committed_keyword_checks + 1
            )
        await self.session.execute(
            update(UsagePeriod)
            .where(UsagePeriod.id == reservation.usage_period_id)
            .values(**values)
        )
        reservation.status = "committed" if commit else "released"
        if commit:
            reservation.committed_at = datetime.now(UTC)
        else:
            reservation.released_at = datetime.now(UTC)
        self.session.add(
            UsageEvent(
                usage_period_id=reservation.usage_period_id,
                user_id=reservation.user_id,
                device_scope=reservation.device_scope,
                event_type="commit" if commit else "release",
                amount=1,
                job_id=job_id,
                batch_id=reservation.batch_id,
                reservation_id=reservation.id,
            )
        )
        await self.session.flush()
        return commit

    async def adjust(
        self, user_id: UUID, actor: UUID, device: str, amount: int, note: str
    ) -> UsagePeriod:
        sub = await self.subscriptions.resolve(user_id, device)
        period = await self.subscriptions.period(sub)
        result = await self.session.execute(
            update(UsagePeriod)
            .where(
                UsagePeriod.id == period.id,
                UsagePeriod.keyword_check_limit + UsagePeriod.adjustment + amount >= 0,
            )
            .values(adjustment=UsagePeriod.adjustment + amount)
            .returning(UsagePeriod.id)
        )
        if result.scalar_one_or_none() is None:
            raise AppError(
                422, "VALIDATION_ERROR", "The effective limit cannot be negative."
            )
        self.session.add(
            UsageEvent(
                usage_period_id=period.id,
                user_id=user_id,
                device_scope=device,
                event_type="adjustment",
                amount=amount,
            )
        )
        self.subscriptions.audit(
            user_id,
            device,
            "usage_adjusted",
            actor=actor,
            subscription=sub,
            metadata={
                "amount": amount,
                "note": note,
                "usage_period_id": str(period.id),
            },
        )
        await self.session.refresh(period)
        return period
