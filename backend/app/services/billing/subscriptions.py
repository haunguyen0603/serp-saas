from calendar import monthrange
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import BillingAuditEvent, Plan, Subscription, UsagePeriod
from app.models.project import Project
from app.models.rank_job import ProjectRankSchedule
from app.repositories.billing import BillingRepository
from app.services.billing.currency import replacement_event

TERMS = (
    "code",
    "name",
    "device_scope",
    "price_monthly_minor_units",
    "currency",
    "max_projects",
    "max_keywords",
    "monthly_keyword_checks",
    "scheduled_checks_enabled",
    "max_scheduled_frequency",
)


def snapshot(plan: Plan) -> dict[str, Any]:
    return {key: getattr(plan, key) for key in TERMS}


def add_months(anchor: datetime, months: int) -> datetime:
    year, month = divmod(anchor.year * 12 + anchor.month - 1 + months, 12)
    return anchor.replace(
        year=year, month=month + 1, day=min(anchor.day, monthrange(year, month + 1)[1])
    )


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BillingRepository(session)

    def audit(
        self,
        user_id: UUID,
        device: str,
        event: str,
        *,
        actor: UUID | None = None,
        subscription: Subscription | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            BillingAuditEvent(
                target_user_id=user_id,
                device_scope=device,
                event_type=event,
                actor_user_id=actor,
                subscription_id=subscription.id if subscription else None,
                plan_id=subscription.plan_id if subscription else None,
                safe_metadata=metadata or {},
            )
        )

    async def disable_schedules(self, sub: Subscription) -> None:
        schedules = await self.session.scalars(
            select(ProjectRankSchedule)
            .join(Project)
            .where(
                Project.user_id == sub.user_id,
                Project.device == sub.device_scope,
                ProjectRankSchedule.enabled.is_(True),
            )
        )
        for schedule in schedules:
            if not sub.snapshot["scheduled_checks_enabled"] or (
                schedule.frequency == "daily"
                and sub.snapshot["max_scheduled_frequency"] != "daily"
            ):
                schedule.enabled = False
                self.audit(
                    sub.user_id,
                    sub.device_scope,
                    "schedule_disabled_due_to_plan",
                    subscription=sub,
                    metadata={
                        "project_id": str(schedule.project_id),
                        "reason": "plan_entitlement",
                    },
                )

    async def resolve(
        self, user_id: UUID, device: str, now: datetime | None = None
    ) -> Subscription:
        if device not in ("desktop", "mobile"):
            raise AppError(422, "PLAN_DEVICE_MISMATCH", "Unsupported device scope.")
        now = now or datetime.now(UTC)
        await self.repo.lock(user_id)
        await self.repo.user(user_id)
        rows = list(
            await self.session.scalars(
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.device_scope == device,
                    Subscription.status.in_(["active", "scheduled"]),
                )
                .order_by(Subscription.period_start)
            )
        )
        active = None
        for sub in rows:
            if sub.period_end <= now:
                sub.status = "expired"
                self.audit(user_id, device, "subscription_expired", subscription=sub)
            elif sub.status == "active":
                active = sub
        # Expire the old active row before activating its successor.
        # ORM UPDATE ordering must not decide partial-unique-index validity.
        await self.session.flush()
        for sub in rows:
            if sub.status == "scheduled" and sub.period_start <= now < sub.period_end:
                if active:
                    await self.close(active, now, "cancelled")
                sub.status, sub.activated_at = "active", now
                active = sub
                self.audit(
                    user_id,
                    device,
                    "subscription_activated",
                    actor=sub.activated_by_user_id,
                    subscription=sub,
                )
        await self.session.flush()
        if active is None:
            plan = await self.repo.plan(f"{device}_free")
            # Explicit Free history, with calendar-month usage until replacement.
            active = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                device_scope=device,
                period_start=now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                ),
                period_end=datetime(9999, 1, 1, tzinfo=UTC),
                snapshot=snapshot(plan),
                activated_at=now,
            )
            self.session.add(active)
            await self.session.flush()
            self.audit(
                user_id,
                device,
                "subscription_activated",
                subscription=active,
                metadata={"reason": "free_fallback"},
            )
        await self.disable_schedules(active)
        return active

    async def period(
        self, sub: Subscription, now: datetime | None = None
    ) -> UsagePeriod:
        now = now or datetime.now(UTC)
        months = (
            (now.year - sub.period_start.year) * 12 + now.month - sub.period_start.month
        )
        if add_months(sub.period_start, months) > now:
            months -= 1
        start = add_months(sub.period_start, months)
        end = min(add_months(sub.period_start, months + 1), sub.period_end)
        period = await self.session.scalar(
            select(UsagePeriod).where(
                UsagePeriod.subscription_id == sub.id, UsagePeriod.period_start == start
            )
        )
        if period is None:
            period = UsagePeriod(
                user_id=sub.user_id,
                subscription_id=sub.id,
                plan_id=sub.plan_id,
                device_scope=sub.device_scope,
                period_start=start,
                period_end=end,
                keyword_check_limit=sub.snapshot["monthly_keyword_checks"],
            )
            self.session.add(period)
            await self.session.flush()
        elif period.period_end < end:
            period.period_end = end
        return period

    async def close(self, sub: Subscription, now: datetime, status: str) -> None:
        sub.status = status
        periods = await self.session.scalars(
            select(UsagePeriod).where(
                UsagePeriod.subscription_id == sub.id,
                UsagePeriod.period_start < now,
                UsagePeriod.period_end > now,
            )
        )
        for period in periods:
            period.period_end = now
        await self.session.flush()

    async def activate(
        self,
        user_id: UUID,
        actor: UUID,
        code: str,
        start: datetime,
        end: datetime,
        payment_method: str | None,
        reference: str | None,
        note: str | None,
        replace_existing: bool = False,
    ) -> Subscription:
        now = datetime.now(UTC)
        if end <= start or end <= now:
            raise AppError(
                422,
                "INVALID_SUBSCRIPTION_PERIOD",
                "The subscription period must end after its start and now.",
            )
        plan = await self.repo.plan(code)
        if payment_method != (
            "manual_bank_transfer" if plan.price_monthly_minor_units else None
        ):
            raise AppError(
                422, "VALIDATION_ERROR", "Paid Plans require a manual bank transfer."
            )
        active = await self.resolve(user_id, plan.device_scope, now)
        future = start > now
        scheduled = await self.session.scalar(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.device_scope == plan.device_scope,
                Subscription.status == "scheduled",
            )
        )
        if scheduled or (
            not future
            and active.snapshot["price_monthly_minor_units"] > 0
            and not replace_existing
        ):
            raise AppError(
                409,
                "SUBSCRIPTION_CONFLICT",
                "A subscription already exists; use Change Plan.",
            )
        if (
            future
            and start < active.period_end
            and active.snapshot["price_monthly_minor_units"] > 0
        ):
            raise AppError(
                409,
                "SUBSCRIPTION_CONFLICT",
                "A scheduled Plan must start after the current subscription ends.",
            )
        if not future:
            await self.close(active, now, "cancelled")
            active.cancelled_at, active.cancelled_by_user_id = now, actor
        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            device_scope=plan.device_scope,
            status="scheduled" if future else "active",
            period_start=start,
            period_end=end,
            snapshot=snapshot(plan),
            payment_method=payment_method,
            payment_reference=reference,
            payment_note=note,
            activated_at=None if future else now,
            activated_by_user_id=actor,
        )
        self.session.add(sub)
        await self.session.flush()
        event = "subscription_scheduled" if future else "subscription_activated"
        if not future and replace_existing:
            event = replacement_event(plan, active.snapshot)
        self.audit(user_id, plan.device_scope, event, actor=actor, subscription=sub)
        if not future:
            await self.disable_schedules(sub)
            await self.period(sub, now)
        return sub

    async def owned(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        await self.repo.lock(user_id)
        sub = await self.session.scalar(
            select(Subscription).where(
                Subscription.id == subscription_id, Subscription.user_id == user_id
            )
        )
        if sub is None:
            raise AppError(404, "NO_ACTIVE_SUBSCRIPTION", "Subscription not found.")
        return sub

    async def extend(
        self, user_id: UUID, actor: UUID, subscription_id: UUID, end: datetime
    ) -> Subscription:
        sub = await self.owned(user_id, subscription_id)
        if sub.status not in ("active", "scheduled") or sub.period_end <= datetime.now(
            UTC
        ):
            raise AppError(
                409, "SUBSCRIPTION_EXPIRED", "Activate a new subscription instead."
            )
        if end <= sub.period_end:
            raise AppError(
                422,
                "INVALID_SUBSCRIPTION_PERIOD",
                "Extension must increase the end date.",
            )
        conflict = await self.session.scalar(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.device_scope == sub.device_scope,
                Subscription.status == "scheduled",
                Subscription.id != sub.id,
                Subscription.period_start < end,
            )
        )
        if conflict:
            raise AppError(
                409, "SUBSCRIPTION_CONFLICT", "Extension overlaps a scheduled Plan."
            )
        previous = sub.period_end
        sub.period_end = end
        self.audit(
            user_id,
            sub.device_scope,
            "subscription_extended",
            actor=actor,
            subscription=sub,
            metadata={"previous_end": previous.isoformat(), "new_end": end.isoformat()},
        )
        if sub.status == "active":
            await self.period(sub)
        return sub

    async def cancel(
        self, user_id: UUID, actor: UUID, subscription_id: UUID
    ) -> Subscription:
        sub = await self.owned(user_id, subscription_id)
        if sub.status in ("active", "scheduled"):
            now = datetime.now(UTC)
            await self.close(sub, now, "cancelled")
            sub.cancelled_at, sub.cancelled_by_user_id = now, actor
            self.audit(
                user_id,
                sub.device_scope,
                "subscription_cancelled",
                actor=actor,
                subscription=sub,
            )
            await self.resolve(user_id, sub.device_scope, now)
        return sub
