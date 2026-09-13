from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingAuditEvent, Subscription, UsageEvent, UsagePeriod
from app.schemas.billing import SubscriptionResponse
from app.services.billing.subscriptions import SubscriptionService
from app.services.normalization import encode_cursor


class BillingViewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.subscriptions = SubscriptionService(session)

    async def summary(self, user_id: UUID) -> dict[str, Any]:
        user = await self.subscriptions.repo.user(user_id)
        devices = []
        for device in ("desktop", "mobile"):
            sub = await self.subscriptions.resolve(user_id, device)
            period = await self.subscriptions.period(sub)
            projects, keywords = await self.subscriptions.repo.counts(user_id, device)
            limit = period.keyword_check_limit + period.adjustment
            devices.append(
                {
                    "device_scope": device,
                    "subscription_id": sub.id,
                    "plan": sub.snapshot,
                    "status": sub.status,
                    "period_start": sub.period_start,
                    "period_end": None
                    if sub.snapshot["price_monthly_minor_units"] == 0
                    else sub.period_end,
                    "projects_used": projects,
                    "keywords_used": keywords,
                    "over_limit": projects > sub.snapshot["max_projects"]
                    or keywords > sub.snapshot["max_keywords"],
                    "usage": {
                        "id": period.id,
                        "period_start": period.period_start,
                        "period_end": period.period_end,
                        "limit": limit,
                        "used": period.committed_keyword_checks,
                        "reserved": period.reserved_keyword_checks,
                        "adjustment": period.adjustment,
                        "remaining": max(
                            0,
                            limit
                            - period.committed_keyword_checks
                            - period.reserved_keyword_checks,
                        ),
                    },
                }
            )
        return {
            "user_id": user.id,
            "email": user.email,
            "account_status": user.status,
            "devices": devices,
        }

    async def history(self, user_id: UUID) -> list[SubscriptionResponse]:
        await self.summary(user_id)
        rows = await self.session.scalars(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc(), Subscription.id.desc())
        )
        return [SubscriptionResponse.model_validate(row) for row in rows]

    async def usage(self, user_id: UUID, internal: bool = False) -> dict[str, Any]:
        summary = await self.summary(user_id)
        periods = await self.session.scalars(
            select(UsagePeriod)
            .where(UsagePeriod.user_id == user_id)
            .order_by(UsagePeriod.period_start.desc())
            .limit(100)
        )
        events = await self.session.scalars(
            select(UsageEvent)
            .where(UsageEvent.user_id == user_id)
            .order_by(UsageEvent.created_at.desc())
            .limit(200)
        )
        result = {
            "devices": summary["devices"],
            "periods": [
                {
                    "id": p.id,
                    "device_scope": p.device_scope,
                    "period_start": p.period_start,
                    "period_end": p.period_end,
                    "limit": p.keyword_check_limit + p.adjustment,
                    "used": p.committed_keyword_checks,
                    "reserved": p.reserved_keyword_checks,
                }
                for p in periods
            ],
            "events": [
                {
                    "id": e.id,
                    "device_scope": e.device_scope,
                    "event_type": e.event_type,
                    "amount": e.amount,
                    "created_at": e.created_at,
                }
                for e in events
            ],
        }
        if internal:
            audits = await self.session.scalars(
                select(BillingAuditEvent)
                .where(BillingAuditEvent.target_user_id == user_id)
                .order_by(BillingAuditEvent.created_at.desc())
                .limit(200)
            )
            result["audit"] = [
                {
                    "id": e.id,
                    "actor_user_id": e.actor_user_id,
                    "event_type": e.event_type,
                    "device_scope": e.device_scope,
                    "safe_metadata": e.safe_metadata,
                    "created_at": e.created_at,
                }
                for e in audits
            ]
        return result

    async def customers(
        self, search: str | None, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        users = await self.subscriptions.repo.customers(search, cursor, limit)
        # Lock users in stable order, matching periodic reconciliation.
        for user_id in sorted(u.id for u in users[:limit]):
            await self.subscriptions.repo.lock(user_id)
        return {
            "items": [await self.summary(u.id) for u in users[:limit]],
            "has_more": len(users) > limit,
            "next_cursor": encode_cursor(
                users[limit - 1].created_at, users[limit - 1].id
            )
            if len(users) > limit
            else None,
        }
