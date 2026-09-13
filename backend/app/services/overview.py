"""Small authenticated aggregation of existing customer data; no analytics."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.rank_job import RankCheckBatch
from app.models.tracked_site import TrackedSite
from app.repositories.rank_job import RankJobRepository
from app.services.billing.views import BillingViewService


class OverviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, user_id: UUID) -> dict[str, Any]:
        billing = await BillingViewService(self.session).summary(user_id)
        rows = (
            await self.session.execute(
                select(RankCheckBatch, Project.name)
                .join(Project, Project.id == RankCheckBatch.project_id)
                .where(RankCheckBatch.user_id == user_id)
                .order_by(RankCheckBatch.requested_at.desc(), RankCheckBatch.id.desc())
                .limit(6)
            )
        ).all()
        repo = RankJobRepository(self.session)
        counts = await repo.counts([batch.id for batch, _ in rows])
        sites = await self.session.scalar(
            select(func.count())
            .select_from(TrackedSite)
            .where(TrackedSite.user_id == user_id, TrackedSite.status == "active")
        )
        return {
            "billing": billing,
            "active_tracked_sites": sites or 0,
            "recent_batches": [
                {
                    **repo.response(batch, counts[batch.id]).model_dump(mode="json"),
                    "project_name": name,
                }
                for batch, name in rows
            ],
        }
