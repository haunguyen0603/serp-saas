"""Mock Google client; validates the real SDK request, without credentials."""

import asyncio
import json
from unittest.mock import Mock
from uuid import uuid4

from google.cloud import tasks_v2

from app.core.config import get_settings
from app.services.task_queue.cloud_tasks import CloudTasksRankCheckQueue


async def main() -> None:
    settings = get_settings().model_copy(
        update={
            "gcp_project_id": "contract-test",
            "gcp_location": "test",
            "cloud_tasks_worker_url": "https://worker.example",
            "cloud_tasks_service_account_email": "tasks@test.iam.gserviceaccount.com",
        }
    )
    client = Mock()
    job = uuid4()
    await CloudTasksRankCheckQueue(settings, client).enqueue_rank_check_job(job)
    request = tasks_v2.CreateTaskRequest(client.create_task.call_args.kwargs["request"])
    assert request.task.name.endswith(f"{job}-rank-check")
    assert (
        request.task.http_request.url
        == "https://worker.example/internal/tasks/rank-check"
    )
    assert request.task.http_request.oidc_token.audience == "https://worker.example"
    assert json.loads(request.task.http_request.body) == {
        "version": 1,
        "job_id": str(job),
    }
    print("PASS: Cloud Tasks name, URL, OIDC, payload; zero GCP operations")


if __name__ == "__main__":
    asyncio.run(main())
