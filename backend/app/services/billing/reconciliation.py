from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.billing.subscriptions import SubscriptionService


async def reconcile_subscriptions(
    session: AsyncSession, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    service = SubscriptionService(session)
    ids = list(await session.scalars(select(User.id).order_by(User.id)))
    for user_id in ids:
        for device in ("desktop", "mobile"):
            sub = await service.resolve(user_id, device, now)
            await service.period(sub, now)
    return len(ids)
