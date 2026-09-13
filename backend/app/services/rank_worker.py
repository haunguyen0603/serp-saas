import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import AppError
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_job import RankCheckBatch, RankCheckJob
from app.repositories.rank_job import TERMINAL_JOBS, RankJobRepository
from app.services.job_execution import JobExecution
from app.services.rank_batches import RankBatchService
from app.services.rank_checks import RankCheckExecutionService
from app.services.serp.router import ProviderRouter

logger = logging.getLogger(__name__)
RETRYABLE = {
    "SERP_PROVIDER_TIMEOUT",
    "SERP_PROVIDER_UNAVAILABLE",
    "SERP_PROVIDER_RATE_LIMITED",
    "RANK_CHECK_PERSISTENCE_ERROR",
    "JOB_INFRASTRUCTURE_ERROR",
    "JOB_TIMEOUT",
}


class RankCheckWorker:
    def __init__(self, batches: RankBatchService, provider: ProviderRouter) -> None:
        self.batches, self.provider = batches, provider

    async def execute(self, job_id: UUID) -> bool:
        """True acknowledges delivery; False asks the transport to retry."""
        now = datetime.now(UTC)
        async with self.batches.factory() as session, session.begin():
            repo = RankJobRepository(session)
            job = await repo.locked_job(job_id)
            if job is None or job.status in TERMINAL_JOBS:
                return True
            if (
                job.status == "running"
                and job.lease_expires_at
                and job.lease_expires_at > now
            ):
                return False
            if job.next_retry_at and job.next_retry_at > now:
                return False
            check = (
                await session.get(RankCheck, job.rank_check_id)
                if job.rank_check_id
                else None
            )
            if check and check.status == RankCheckStatus.SUCCEEDED:
                job.status, job.completed_at = "succeeded", check.completed_at
                job.lease_expires_at = None
                await repo.reconcile(job.batch_id)
                return True
            if job.attempt_count >= job.max_attempts:
                job.status, job.completed_at, job.last_error_code = (
                    "failed",
                    now,
                    "JOB_MAX_ATTEMPTS",
                )
                job.lease_expires_at = None
                if check and check.status == RankCheckStatus.RUNNING:
                    check.status, check.completed_at, check.error_code = (
                        RankCheckStatus.FAILED,
                        now,
                        "JOB_MAX_ATTEMPTS",
                    )
                await repo.reconcile(job.batch_id)
                return True
            job.status = "running"
            job.attempt_count += 1
            job.started_at = job.started_at or now
            job.worker_execution_id = uuid4()
            job.lease_expires_at = now + timedelta(
                seconds=self.batches.settings.rank_check_job_lease_seconds
            )
            job.next_retry_at = None
            execution = JobExecution(job.id, job.worker_execution_id)
            await repo.reconcile(job.batch_id)
        fields = {
            "job_id": str(job.id),
            "batch_id": str(job.batch_id),
            "worker_execution_id": str(execution.execution_id),
            "attempt_count": job.attempt_count,
        }
        logger.info("rank_check_job_claimed", extra=fields)
        service = RankCheckExecutionService(
            self.batches.factory,
            self.provider,
            self.batches.settings,
            job_execution=execution,
        )
        error: str | None = None
        try:
            async with asyncio.timeout(
                self.batches.settings.rank_check_job_lease_seconds - 5
            ):
                result = await service.execute_rank_check(
                    job.project_id, job.keyword_id, job.user_id
                )
                error = (
                    result.error_code
                    if result.status == RankCheckStatus.FAILED
                    else None
                )
        except AppError as exc:
            if exc.code == "JOB_LEASE_LOST":
                return False
            error = exc.code
        except TimeoutError:
            error = "JOB_TIMEOUT"
        except Exception:
            error = "JOB_INFRASTRUCTURE_ERROR"
        try:
            async with self.batches.factory() as session, session.begin():
                repo = RankJobRepository(session)
                current = await repo.locked_job(job_id)
                if (
                    current is None
                    or current.worker_execution_id != execution.execution_id
                    or current.status != "running"
                ):
                    return False
                check = (
                    await session.get(RankCheck, current.rank_check_id)
                    if current.rank_check_id
                    else None
                )
                if check and check.status == RankCheckStatus.SUCCEEDED:
                    error = None
                retry = (
                    error in RETRYABLE and current.attempt_count < current.max_attempts
                )
                current.last_error_code, current.lease_expires_at = error, None
                if retry:
                    current.status = "queued"
                    delay = min(
                        self.batches.settings.task_max_backoff_seconds,
                        self.batches.settings.task_min_backoff_seconds
                        * 2 ** (current.attempt_count - 1),
                    )
                    current.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
                else:
                    current.status = "failed" if error else "succeeded"
                    current.completed_at = datetime.now(UTC)
                if error and check and check.status == RankCheckStatus.RUNNING:
                    check.status, check.completed_at, check.error_code = (
                        RankCheckStatus.FAILED,
                        datetime.now(UTC),
                        error,
                    )
                await repo.reconcile(current.batch_id)
                fields.update(
                    {
                        "rank_check_id": str(current.rank_check_id),
                        "safe_error_code": error,
                        "duration_ms": int(
                            (datetime.now(UTC) - now).total_seconds() * 1000
                        ),
                    }
                )
                logger.info(
                    "rank_check_job_retry"
                    if retry
                    else "rank_check_job_failed"
                    if error
                    else "rank_check_job_succeeded",
                    extra=fields,
                )
            return not retry
        except SQLAlchemyError:
            return False

    async def recover(self, *, local: bool = False, limit: int = 100) -> int:
        now = datetime.now(UTC)
        async with self.batches.factory() as session:
            pending = list(
                await session.scalars(
                    select(RankCheckJob.id)
                    .where(RankCheckJob.status == "pending")
                    .order_by(RankCheckJob.created_at)
                    .limit(limit)
                )
            )
        for pending_id in pending:
            async with self.batches.factory() as session, session.begin():
                repo = RankJobRepository(session)
                stranded = await repo.locked_job(pending_id)
                if (
                    stranded
                    and stranded.status == "pending"
                    and stranded.created_at
                    < now
                    - timedelta(
                        seconds=self.batches.settings.task_max_retry_duration_seconds
                    )
                ):
                    stranded.status, stranded.completed_at = "failed", now
                    stranded.last_error_code = "TASK_ENQUEUE_EXHAUSTED"
                    await repo.reconcile(stranded.batch_id)
        for offset in range(0, len(pending), 10):
            await asyncio.gather(
                *(
                    self.batches.enqueue(job_id)
                    for job_id in pending[offset : offset + 10]
                )
            )
        async with self.batches.factory() as session:
            statement = (
                select(RankCheckJob.id)
                .where(
                    (
                        (RankCheckJob.status == "running")
                        & (RankCheckJob.lease_expires_at <= now)
                    )
                    | (
                        (RankCheckJob.status == "queued")
                        & (
                            RankCheckJob.next_retry_at.is_(None)
                            | (RankCheckJob.next_retry_at <= now)
                        )
                    )
                )
                .order_by(RankCheckJob.created_at)
                .limit(limit)
            )
            ids = list(await session.scalars(statement))
        if local:
            for job_id in ids:
                await self.execute(job_id)
        else:
            # Cloud Tasks owns retries. Jobs stranded past the queue's retry
            # horizon are terminally reconciled; deterministic task tombstones
            # must never be mistaken for a fresh deliverable task.
            async with self.batches.factory() as session:
                stale = list(
                    await session.scalars(
                        select(RankCheckJob.id)
                        .where(
                            RankCheckJob.status.in_(["pending", "queued", "running"]),
                            RankCheckJob.updated_at
                            < now
                            - timedelta(
                                seconds=self.batches.settings.task_max_retry_duration_seconds
                                + self.batches.settings.rank_check_job_lease_seconds
                            ),
                        )
                        .limit(limit)
                    )
                )
            for job_id in stale:
                async with self.batches.factory() as session, session.begin():
                    repo = RankJobRepository(session)
                    job = await repo.locked_job(job_id)
                    if (
                        job
                        and job.status not in TERMINAL_JOBS
                        and (not job.lease_expires_at or job.lease_expires_at <= now)
                    ):
                        check = (
                            await session.get(RankCheck, job.rank_check_id)
                            if job.rank_check_id
                            else None
                        )
                        job.status = (
                            "succeeded"
                            if check and check.status == RankCheckStatus.SUCCEEDED
                            else "failed"
                        )
                        job.completed_at, job.lease_expires_at = now, None
                        job.last_error_code = (
                            None
                            if job.status == "succeeded"
                            else "TASK_DELIVERY_EXHAUSTED"
                        )
                        if check and check.status == RankCheckStatus.RUNNING:
                            check.status, check.completed_at, check.error_code = (
                                RankCheckStatus.FAILED,
                                now,
                                "TASK_DELIVERY_EXHAUSTED",
                            )
                        await repo.reconcile(job.batch_id)
        async with self.batches.factory() as session, session.begin():
            batches = list(
                await session.scalars(
                    select(RankCheckBatch.id)
                    .where(RankCheckBatch.completed_at.is_(None))
                    .order_by(RankCheckBatch.updated_at)
                    .limit(limit)
                )
            )
            for batch_id in batches:
                await RankJobRepository(session).reconcile(batch_id)
        return len(pending) + (len(ids) if local else 0)
