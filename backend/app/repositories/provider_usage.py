from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_usage import ProviderUsage


def monthly_period_key(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m")


class ProviderUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reserve_request(self, provider: str, budget: int | None) -> bool:
        period_key = monthly_period_key()
        await self.session.execute(
            insert(ProviderUsage)
            .values(provider=provider, period_type="monthly", period_key=period_key)
            .on_conflict_do_nothing(constraint="uq_provider_usage_period")
        )
        usage = cast(
            ProviderUsage,
            await self.session.scalar(
                select(ProviderUsage)
                .where(
                    ProviderUsage.provider == provider,
                    ProviderUsage.period_type == "monthly",
                    ProviderUsage.period_key == period_key,
                )
                .with_for_update()
            ),
        )
        if budget is not None and usage.request_count >= budget:
            return False
        usage.request_count += 1
        usage.updated_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def record_outcome(
        self,
        provider: str,
        *,
        successes: int = 0,
        failures: int = 0,
        fallbacks: int = 0,
    ) -> None:
        period_key = monthly_period_key()
        usage = cast(
            ProviderUsage | None,
            await self.session.scalar(
                select(ProviderUsage)
                .where(
                    ProviderUsage.provider == provider,
                    ProviderUsage.period_type == "monthly",
                    ProviderUsage.period_key == period_key,
                )
                .with_for_update()
            ),
        )
        if usage is None:
            return
        usage.success_count += successes
        usage.failure_count += failures
        usage.fallback_count += fallbacks
        usage.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def current(self, provider: str) -> ProviderUsage | None:
        return cast(
            ProviderUsage | None,
            await self.session.scalar(
                select(ProviderUsage).where(
                    ProviderUsage.provider == provider,
                    ProviderUsage.period_type == "monthly",
                    ProviderUsage.period_key == monthly_period_key(),
                )
            ),
        )
