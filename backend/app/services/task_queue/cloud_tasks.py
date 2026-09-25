import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from google.api_core.exceptions import (
    AlreadyExists,
    InvalidArgument,
    NotFound,
    PermissionDenied,
    Unauthenticated,
)
from google.cloud import tasks_v2

from app.core.config import Settings
from app.services.task_queue.base import TaskEnqueueResult, TaskQueueError

logger = logging.getLogger(__name__)


class CloudTasksRankCheckQueue:
    def __init__(self, settings: Settings, client: Any = None) -> None:
        self.settings = settings
        self.client = client or tasks_v2.CloudTasksClient()

    async def enqueue_rank_check_job(
        self, job_id: UUID, *, schedule_time: datetime | None = None
    ) -> TaskEnqueueResult:
        s = self.settings
        parent = (
            f"projects/{s.gcp_project_id}/locations/{s.gcp_location}"
            f"/queues/{s.cloud_tasks_queue}"
        )
        name = f"{parent}/tasks/{job_id}-rank-check"
        task: dict[str, Any] = {
            "name": name,
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": s.cloud_tasks_worker_url.rstrip("/")
                + "/internal/tasks/rank-check",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"version": 1, "job_id": str(job_id)}).encode(),
                "oidc_token": {
                    "service_account_email": s.cloud_tasks_service_account_email,
                    "audience": s.cloud_tasks_worker_url.rstrip("/"),
                },
            },
            "dispatch_deadline": {"seconds": s.rank_check_job_lease_seconds},
        }
        if schedule_time:
            task["schedule_time"] = schedule_time
        try:
            await asyncio.to_thread(
                self.client.create_task,
                request={"parent": parent, "task": task},
                timeout=5,
                retry=None,
            )
        except AlreadyExists:
            logger.info("cloud_task_already_exists", extra={"job_id": str(job_id)})
            return TaskEnqueueResult(name, already_exists=True)
        except (InvalidArgument, NotFound, PermissionDenied, Unauthenticated):
            raise TaskQueueError("TASK_ENQUEUE_FAILED", permanent=True) from None
        except Exception:
            logger.warning(
                "cloud_task_enqueue_failed",
                extra={"job_id": str(job_id), "safe_error_code": "TASK_ENQUEUE_FAILED"},
            )
            raise TaskQueueError("TASK_ENQUEUE_FAILED") from None
        return TaskEnqueueResult(name)

    async def enqueue_report_job(
        self,
        report_id: UUID,
        *,
        schedule_time: datetime | None = None,
        attempt: int = 0,
    ) -> TaskEnqueueResult:
        s = self.settings
        parent = (
            f"projects/{s.gcp_project_id}/locations/{s.gcp_location}"
            f"/queues/{s.cloud_tasks_queue}"
        )
        name = f"{parent}/tasks/{report_id}-report-{attempt}"
        task: dict[str, Any] = {
            "name": name,
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": s.cloud_tasks_worker_url.rstrip("/") + "/internal/tasks/report",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"version": 1, "report_id": str(report_id)}
                ).encode(),
                "oidc_token": {
                    "service_account_email": s.cloud_tasks_service_account_email,
                    "audience": s.cloud_tasks_worker_url.rstrip("/"),
                },
            },
            "dispatch_deadline": {"seconds": s.report_job_lease_seconds},
        }
        if schedule_time:
            task["schedule_time"] = schedule_time
        try:
            await asyncio.to_thread(
                self.client.create_task,
                request={"parent": parent, "task": task},
                timeout=5,
                retry=None,
            )
        except AlreadyExists:
            logger.info(
                "report_task_already_exists", extra={"report_id": str(report_id)}
            )
            return TaskEnqueueResult(name, already_exists=True)
        except (InvalidArgument, NotFound, PermissionDenied, Unauthenticated):
            raise TaskQueueError("REPORT_TASK_ENQUEUE_FAILED", permanent=True) from None
        except Exception:
            logger.warning(
                "report_task_enqueue_failed",
                extra={
                    "report_id": str(report_id),
                    "safe_error_code": "REPORT_TASK_ENQUEUE_FAILED",
                },
            )
            raise TaskQueueError("REPORT_TASK_ENQUEUE_FAILED") from None
        return TaskEnqueueResult(name)
