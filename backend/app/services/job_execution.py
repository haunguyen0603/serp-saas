"""Fencing for the existing ranking pipeline, including crash-safe check linkage."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.rank_job import RankCheckJob


@dataclass(frozen=True)
class JobExecution:
    job_id: UUID
    execution_id: UUID

    async def lock(self, session: AsyncSession) -> RankCheckJob:
        job = await session.scalar(
            select(RankCheckJob).where(RankCheckJob.id == self.job_id).with_for_update()
        )
        if (
            job is None
            or job.status != "running"
            or job.worker_execution_id != self.execution_id
            or job.lease_expires_at is None
            or job.lease_expires_at <= datetime.now(UTC)
        ):
            raise AppError(409, "JOB_LEASE_LOST", "The execution lease has expired.")
        return job
