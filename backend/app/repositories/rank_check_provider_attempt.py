from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
