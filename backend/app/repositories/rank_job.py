import logging
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import UsageReservation
from app.models.rank_job import RankCheckBatch, RankCheckJob
from app.repositories.project import ProjectRepository
from app.schemas.rank_job import BatchResponse

logger = logging.getLogger(__name__)

TERMINAL_JOBS = {"succeeded", "failed", "cancelled"}
TERMINAL_BATCHES = {"completed", "completed_with_errors", "failed", "cancelled"}


class RankJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require_project(self, project_id: UUID, user_id: UUID) -> None:
        if (
            await ProjectRepository(self.session).get_for_user(project_id, user_id)
            is None
        ):
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")

    async def batch(
        self, batch_id: UUID, project_id: UUID, user_id: UUID, *, lock: bool = False
    ) -> RankCheckBatch:
        statement = select(RankCheckBatch).where(
            RankCheckBatch.id == batch_id,
            RankCheckBatch.project_id == project_id,
            RankCheckBatch.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        batch = await self.session.scalar(statement)
        if batch is None:
            raise AppError(404, "BATCH_NOT_FOUND", "Batch not found.")
        return batch

    async def locked_job(self, job_id: UUID) -> RankCheckJob | None:
        batch_id = await self.session.scalar(
            select(RankCheckJob.batch_id).where(RankCheckJob.id == job_id)
        )
        if batch_id is None:
            return None
        # Every state transition takes the batch lock first. Reconciliation sees
        # committed peers and our own flush, without lost completion updates.
        await self.session.scalar(
            select(RankCheckBatch)
            .where(RankCheckBatch.id == batch_id)
            .with_for_update()
        )
        return cast(
            RankCheckJob | None,
            await self.session.scalar(
                select(RankCheckJob).where(RankCheckJob.id == job_id).with_for_update()
            ),
        )

    async def counts(self, batch_ids: list[UUID]) -> dict[UUID, dict[str, int]]:
        rows = (
            await self.session.execute(
                select(RankCheckJob.batch_id, RankCheckJob.status, func.count())
                .where(RankCheckJob.batch_id.in_(batch_ids))
                .group_by(RankCheckJob.batch_id, RankCheckJob.status)
            )
        ).all()
        result: dict[UUID, dict[str, int]] = {key: {} for key in batch_ids}
        for batch_id, status, count in rows:
            result[batch_id][status] = count
        return result

    async def reconcile(self, batch_id: UUID) -> None:
        batch = await self.session.scalar(
            select(RankCheckBatch)
            .where(RankCheckBatch.id == batch_id)
            .with_for_update()
        )
        if batch is None:
            return
        await self.session.flush()
        from app.services.billing.usage import UsageService

        terminal_jobs = await self.session.scalars(
            select(RankCheckJob.id)
            .join(UsageReservation, UsageReservation.job_id == RankCheckJob.id)
            .where(
                RankCheckJob.batch_id == batch_id,
                RankCheckJob.status.in_(TERMINAL_JOBS),
                UsageReservation.status == "reserved",
            )
        )
        for job_id in terminal_jobs:
            await UsageService(self.session).settle(job_id, False)
        counts = (await self.counts([batch_id]))[batch_id]
        now = datetime.now(UTC)
        terminal = sum(counts.get(s, 0) for s in TERMINAL_JOBS)
        if terminal == batch.requested_keyword_count:
            batch.status = (
                "completed_with_errors"
                if counts.get("failed")
                else "cancelled"
                if counts.get("cancelled")
                else "completed"
            )
            if batch.completed_at is None:
                logger.info(
                    "rank_check_batch_completed",
                    extra={
                        "batch_id": str(batch.id),
                        "duration_ms": int(
                            (now - batch.requested_at).total_seconds() * 1000
                        ),
                    },
                )
            batch.completed_at = batch.completed_at or now
        elif counts.get("running") or terminal:
            batch.status = "running"
        elif counts.get("pending"):
            batch.status = "pending"
        else:
            batch.status = "queued"
        if counts.get("running"):
            batch.started_at = batch.started_at or now

    @staticmethod
    def response(batch: RankCheckBatch, counts: dict[str, int]) -> BatchResponse:
        result = BatchResponse.model_validate(batch)
        result.queued_keyword_count = counts.get("queued", 0)
        result.running_keyword_count = counts.get("running", 0)
        result.succeeded_keyword_count = counts.get("succeeded", 0)
        result.failed_keyword_count = counts.get("failed", 0)
        result.cancelled_keyword_count = counts.get("cancelled", 0)
        terminal = sum(counts.get(s, 0) for s in TERMINAL_JOBS)
        result.progress_percent = (
            round(100 * terminal / batch.requested_keyword_count, 1)
            if batch.requested_keyword_count
            else 100
        )
        return result

    async def batches(
        self,
        project_id: UUID,
        user_id: UUID,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[RankCheckBatch]:
        statement = select(RankCheckBatch).where(
            RankCheckBatch.project_id == project_id, RankCheckBatch.user_id == user_id
        )
        if cursor:
            statement = statement.where(
                tuple_(RankCheckBatch.created_at, RankCheckBatch.id) < cursor
            )
        return list(
            await self.session.scalars(
                statement.order_by(
                    RankCheckBatch.created_at.desc(), RankCheckBatch.id.desc()
                ).limit(limit + 1)
            )
        )

    async def jobs(
        self, batch_id: UUID, limit: int, cursor: tuple[datetime, UUID] | None
    ) -> list[RankCheckJob]:
        statement = select(RankCheckJob).where(RankCheckJob.batch_id == batch_id)
        if cursor:
            statement = statement.where(
                tuple_(RankCheckJob.created_at, RankCheckJob.id) < cursor
            )
        return list(
            await self.session.scalars(
                statement.order_by(
                    RankCheckJob.created_at.desc(), RankCheckJob.id.desc()
                ).limit(limit + 1)
            )
        )
