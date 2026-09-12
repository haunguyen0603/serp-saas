from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ranking import Ranking
from app.services.domain_matching import MatchedOrganicResult


class RankingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_many(
        self, rank_check_id: UUID, matches: list[MatchedOrganicResult]
    ) -> list[Ranking]:
        rows = [
            Ranking(
                rank_check_id=rank_check_id,
                tracked_site_id=match.tracked_site_id,
                tracked_domain_id=match.tracked_domain_id,
                tracked_site_name_snapshot=match.tracked_site_name,
                matched_domain_snapshot=match.matched_domain,
                position=match.position,
                result_url=match.result_url,
                result_hostname=match.result_hostname,
                title=match.title or None,
            )
            for match in matches
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_for_checks(self, check_ids: list[UUID]) -> list[Ranking]:
        if not check_ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(Ranking)
                    .where(Ranking.rank_check_id.in_(check_ids))
                    .order_by(Ranking.position)
                )
            ).all()
        )

    async def has_for_site(self, site_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(Ranking.id).where(Ranking.tracked_site_id == site_id).limit(1)
            )
        )

    async def has_for_domain(self, domain_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(Ranking.id)
                .where(Ranking.tracked_domain_id == domain_id)
                .limit(1)
            )
        )
