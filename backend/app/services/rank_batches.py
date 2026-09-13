import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.models.keyword import Keyword
from app.models.project import ProjectStatus
from app.models.rank_job import RankCheckBatch, RankCheckJob
from app.repositories.project import ProjectRepository
from app.repositories.rank_job import RankJobRepository
from app.schemas.rank_job import (
    BatchAccepted,
    BatchList,
    BatchResponse,
    JobList,
    JobResponse,
)
from app.services.billing.entitlements import EntitlementService
from app.services.billing.usage import UsageService
from app.services.normalization import decode_cursor, encode_cursor
from app.services.task_queue import RankCheckTaskQueue, TaskQueueError

logger = logging.getLogger(__name__)


class RankBatchService:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        queue: RankCheckTaskQueue,
    ) -> None:
        self.factory, self.settings, self.queue = factory, settings, queue

    async def create_rows(
        self,
        session: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        keyword_ids: list[UUID] | None,
        trigger: str,
        *,
        schedule_id: UUID | None = None,
        scheduled_for: datetime | None = None,
    ) -> tuple[RankCheckBatch, list[RankCheckJob]]:
        await UsageService(session).subscriptions.repo.lock(user_id)
        project = await ProjectRepository(session).get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        if project.status != ProjectStatus.ACTIVE:
            raise AppError(400, "PROJECT_NOT_ACTIVE", "The Project is archived.")
        statement = select(Keyword).where(
            Keyword.project_id == project_id, Keyword.active.is_(True)
        )
        if keyword_ids is not None:
            statement = statement.where(Keyword.id.in_(keyword_ids))
        keywords = list(
            await session.scalars(
                statement.limit(self.settings.rank_check_batch_max_keywords + 1)
            )
        )
        if len(keywords) > self.settings.rank_check_batch_max_keywords:
            raise AppError(
                400, "RANK_CHECK_LIMIT_EXCEEDED", "Too many keywords in this batch."
            )
        if keyword_ids is not None and len(keywords) != len(set(keyword_ids)):
            raise AppError(
                400,
                "KEYWORD_NOT_ACTIVE",
                "Selected Keywords must exist and be active in this Project.",
            )
        if not keywords:
            raise AppError(400, "NO_ACTIVE_KEYWORDS", "Add an active Keyword first.")
        if trigger == "scheduled":
            from app.models.rank_job import ProjectRankSchedule

            schedule = await session.get(ProjectRankSchedule, schedule_id)
            if schedule is None:
                raise AppError(404, "SCHEDULE_NOT_INCLUDED", "Schedule not found.")
            await EntitlementService(session).schedule(
                user_id, project.device, schedule.frequency
            )
        period = await UsageService(session).reserve(
            user_id, project.device, len(keywords)
        )
        batch = RankCheckBatch(
            project_id=project_id,
            user_id=user_id,
            trigger_type=trigger,
            requested_keyword_count=len(keywords),
            schedule_id=schedule_id,
            scheduled_for=scheduled_for,
        )
        session.add(batch)
        await session.flush()
        jobs = [
            RankCheckJob(
                batch_id=batch.id,
                user_id=user_id,
                project_id=project_id,
                keyword_id=k.id,
                max_attempts=self.settings.rank_check_job_max_attempts,
            )
            for k in keywords
        ]
        session.add_all(jobs)
        await session.flush()
        UsageService(session).attach(period, jobs)
        await session.flush()
        logger.info(
            "rank_check_batch_created",
            extra={
                "batch_id": str(batch.id),
                "project_id": str(project_id),
                "user_id": str(user_id),
                "trigger_type": trigger,
            },
        )
        for job in jobs:
            logger.info(
                "rank_check_job_created",
                extra={"job_id": str(job.id), "batch_id": str(batch.id)},
            )
        return batch, jobs

    async def create(
        self,
        project_id: UUID,
        user_id: UUID,
        keyword_ids: list[UUID] | None = None,
        trigger: str = "manual_project",
    ) -> BatchAccepted:
        async with self.factory() as session, session.begin():
            batch, jobs = await self.create_rows(
                session, project_id, user_id, keyword_ids, trigger
            )
        # Bounded first chunk: large batches are a durable outbox for dispatcher.
        await asyncio.gather(*(self.enqueue(job.id) for job in jobs[:10]))
        detail = await self.detail(project_id, user_id, batch.id)
        return BatchAccepted(
            batch_id=batch.id,
            job_id=jobs[0].id if len(jobs) == 1 else None,
            status=detail.status,
            requested_keyword_count=len(jobs),
        )

    async def enqueue(self, job_id: UUID) -> bool:
        async with self.factory() as session:
            job = await session.get(RankCheckJob, job_id)
            if job is None or job.status != "pending":
                return False
            schedule_time = job.next_retry_at
        try:
            result = await self.queue.enqueue_rank_check_job(
                job_id, schedule_time=schedule_time
            )
        except TaskQueueError as error:
            if getattr(error, "permanent", False):
                async with self.factory() as session, session.begin():
                    repo = RankJobRepository(session)
                    failed = await repo.locked_job(job_id)
                    if failed and failed.status == "pending":
                        failed.status, failed.completed_at = "failed", datetime.now(UTC)
                        failed.last_error_code = "TASK_ENQUEUE_FAILED"
                        await repo.reconcile(failed.batch_id)
            return False
        async with self.factory() as session, session.begin():
            repo = RankJobRepository(session)
            job = await repo.locked_job(job_id)
            if job is not None and job.status == "pending":
                job.status, job.task_name = "queued", result.task_name
                job.queued_at = datetime.now(UTC)
                await repo.reconcile(job.batch_id)
                logger.info(
                    "rank_check_job_enqueued",
                    extra={"job_id": str(job.id), "batch_id": str(job.batch_id)},
                )
        return True

    async def detail(
        self, project_id: UUID, user_id: UUID, batch_id: UUID
    ) -> BatchResponse:
        async with self.factory() as session:
            repo = RankJobRepository(session)
            batch = await repo.batch(batch_id, project_id, user_id)
            return repo.response(batch, (await repo.counts([batch.id]))[batch.id])

    async def history(
        self, project_id: UUID, user_id: UUID, limit: int, cursor: str | None
    ) -> BatchList:
        async with self.factory() as session:
            repo = RankJobRepository(session)
            await repo.require_project(project_id, user_id)
            rows = await repo.batches(project_id, user_id, limit, decode_cursor(cursor))
            counts = await repo.counts([b.id for b in rows])
            return BatchList(
                items=[repo.response(b, counts[b.id]) for b in rows[:limit]],
                has_more=len(rows) > limit,
                next_cursor=encode_cursor(
                    rows[limit - 1].created_at, rows[limit - 1].id
                )
                if len(rows) > limit
                else None,
            )

    async def jobs(
        self,
        project_id: UUID,
        user_id: UUID,
        batch_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> JobList:
        async with self.factory() as session:
            repo = RankJobRepository(session)
            await repo.batch(batch_id, project_id, user_id)
            rows = await repo.jobs(batch_id, limit, decode_cursor(cursor))
            name_rows = (
                await session.execute(
                    select(Keyword.id, Keyword.keyword).where(
                        Keyword.id.in_([j.keyword_id for j in rows[:limit]])
                    )
                )
            ).all()
            names = {key: name for key, name in name_rows}
            items = [JobResponse.model_validate(j) for j in rows[:limit]]
            for item in items:
                item.keyword = names[item.keyword_id]
            return JobList(
                items=items,
                has_more=len(rows) > limit,
                next_cursor=encode_cursor(
                    rows[limit - 1].created_at, rows[limit - 1].id
                )
                if len(rows) > limit
                else None,
            )

    async def cancel(
        self, project_id: UUID, user_id: UUID, batch_id: UUID
    ) -> BatchResponse:
        async with self.factory() as session, session.begin():
            repo = RankJobRepository(session)
            await repo.batch(batch_id, project_id, user_id, lock=True)
            jobs = await session.scalars(
                select(RankCheckJob)
                .where(
                    RankCheckJob.batch_id == batch_id,
                    RankCheckJob.status.in_(["pending", "queued"]),
                )
                .with_for_update()
            )
            for job in jobs:
                job.status, job.completed_at = "cancelled", datetime.now(UTC)
                logger.info(
                    "rank_check_job_cancelled",
                    extra={"job_id": str(job.id), "batch_id": str(batch_id)},
                )
            await repo.reconcile(batch_id)
        return await self.detail(project_id, user_id, batch_id)
