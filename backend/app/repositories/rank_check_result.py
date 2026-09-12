from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rank_check_result import RankCheckResult
from app.services.serp.types import OrganicResult


class RankCheckResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(
        self, rank_check_id: UUID, results: tuple[OrganicResult, ...]
    ) -> list[RankCheckResult]:
        rows = [
            RankCheckResult(
                rank_check_id=rank_check_id,
                position=result.position,
                title=result.title or None,
                url=result.url,
                hostname=result.hostname,
                displayed_url=result.displayed_url,
                snippet=result.snippet,
            )
            for result in results
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_for_checks(self, check_ids: list[UUID]) -> list[RankCheckResult]:
        if not check_ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(RankCheckResult)
                    .where(RankCheckResult.rank_check_id.in_(check_ids))
                    .order_by(RankCheckResult.position)
                )
            ).all()
        )
