from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TaskEnqueueResult:
    task_name: str
    already_exists: bool = False


class TaskQueueError(Exception):
    """Safe infrastructure error; never includes SDK exception text."""

    def __init__(self, code: str, *, permanent: bool = False) -> None:
        super().__init__(code)
        self.permanent = permanent


class RankCheckTaskQueue(Protocol):
    async def enqueue_ranking_alerts(self, *, attempt: int) -> TaskEnqueueResult: ...

    async def enqueue_rank_check_job(
        self, job_id: UUID, *, schedule_time: datetime | None = None
    ) -> TaskEnqueueResult: ...

    async def enqueue_report_job(
        self,
        report_id: UUID,
        *,
        schedule_time: datetime | None = None,
        attempt: int = 0,
    ) -> TaskEnqueueResult: ...
