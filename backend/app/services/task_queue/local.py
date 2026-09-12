from datetime import datetime
from uuid import UUID

from app.services.task_queue.base import TaskEnqueueResult


class LocalTaskQueue:
    """Deterministic acceptance; local runner reads durable DB jobs."""

    async def enqueue_rank_check_job(
        self, job_id: UUID, *, schedule_time: datetime | None = None
    ) -> TaskEnqueueResult:
        return TaskEnqueueResult(f"local/rank-check-{job_id}")
