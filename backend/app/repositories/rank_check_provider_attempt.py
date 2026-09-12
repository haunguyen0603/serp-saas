from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rank_check import RankCheck
from app.models.rank_check_provider_attempt import (
    ProviderAttemptStatus,
    RankCheckProviderAttempt,
)


class RankCheckProviderAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        rank_check_id: UUID,
        provider: str,
        attempt_number: int,
        status: ProviderAttemptStatus,
        started_at: datetime,
        completed_at: datetime,
        provider_request_count: int,
        error_code: str | None = None,
    ) -> RankCheckProviderAttempt:
        # Continue numbering across job retries; router fallback numbering remains
        # local to a single search invocation. Lock only during DB persistence.
        check = await self.session.scalar(
            select(RankCheck).where(RankCheck.id == rank_check_id).with_for_update()
        )
        maximum = await self.session.scalar(
            select(func.max(RankCheckProviderAttempt.attempt_number)).where(
                RankCheckProviderAttempt.rank_check_id == rank_check_id
            )
        )
        attempt_number = max(attempt_number, (maximum or 0) + 1)
        attempt = RankCheckProviderAttempt(
            rank_check_id=rank_check_id,
            provider=provider,
            attempt_number=attempt_number,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            provider_request_count=provider_request_count,
            error_code=error_code,
        )
        self.session.add(attempt)
        await self.session.flush()
        # A fenced-out worker can finish its provider attempt after its successor.
        # Keep accounting exact even though it may no longer persist SERP results.
        if check is not None:
            check.provider_request_count = int(
                await self.session.scalar(
                    select(
                        func.sum(RankCheckProviderAttempt.provider_request_count)
                    ).where(RankCheckProviderAttempt.rank_check_id == rank_check_id)
                )
                or 0
            )
        return attempt

    async def list_for_checks(
        self, check_ids: list[UUID]
    ) -> list[RankCheckProviderAttempt]:
        if not check_ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(RankCheckProviderAttempt)
                    .where(RankCheckProviderAttempt.rank_check_id.in_(check_ids))
                    .order_by(
                        RankCheckProviderAttempt.rank_check_id,
                        RankCheckProviderAttempt.attempt_number,
                    )
                )
            ).all()
        )
