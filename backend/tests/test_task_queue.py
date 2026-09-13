import json
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from google.api_core.exceptions import AlreadyExists, ServiceUnavailable
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.rank_job import ScheduleRequest, TaskPayload
from app.services.rank_schedules import next_run
from app.services.task_queue import TaskQueueError
from app.services.task_queue.cloud_tasks import CloudTasksRankCheckQueue
from app.services.task_queue.local import LocalTaskQueue


def cloud_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "task_queue_provider": "cloud_tasks",
            "gcp_project_id": "test-project",
            "gcp_location": "test-region",
            "cloud_tasks_worker_url": "https://worker.example",
            "cloud_tasks_service_account_email": "tasks@test.iam.gserviceaccount.com",
            "scheduler_service_account_email": "cron@test.iam.gserviceaccount.com",
        }
    )


async def test_local_deterministic(settings: Settings):
    queue = LocalTaskQueue()
    job = uuid4()
    assert await queue.enqueue_rank_check_job(
        job
    ) == await queue.enqueue_rank_check_job(job)


async def test_cloud_task_contract_and_deduplication(settings: Settings):
    client = Mock()
    queue = CloudTasksRankCheckQueue(cloud_settings(settings), client)
    job = uuid4()
    at = datetime(2026, 9, 12, tzinfo=UTC)
    result = await queue.enqueue_rank_check_job(job, schedule_time=at)
    request = client.create_task.call_args.kwargs["request"]
    task = request["task"]
    assert task["name"] == (
        "projects/test-project/locations/test-region/queues/rank-checks/tasks/"
        f"{job}-rank-check"
    )
    assert task["schedule_time"] == at
    assert json.loads(task["http_request"]["body"]) == {
        "version": 1,
        "job_id": str(job),
    }
    assert (
        task["http_request"]["url"]
        == "https://worker.example/internal/tasks/rank-check"
    )
    assert task["http_request"]["oidc_token"] == {
        "audience": "https://worker.example",
        "service_account_email": "tasks@test.iam.gserviceaccount.com",
    }
    # Validate SDK serialization, not just an arbitrary mock dictionary.
    from google.cloud import tasks_v2

    serialized = tasks_v2.CreateTaskRequest(request)
    assert serialized.task.http_request.body == task["http_request"]["body"]
    client.create_task.side_effect = AlreadyExists("private SDK detail")
    duplicate = await queue.enqueue_rank_check_job(job)
    assert duplicate.task_name == result.task_name and duplicate.already_exists
    client.create_task.side_effect = ServiceUnavailable("private SDK detail")
    with pytest.raises(TaskQueueError, match="^TASK_ENQUEUE_FAILED$"):
        await queue.enqueue_rank_check_job(job)


@pytest.mark.parametrize(
    "extra",
    [
        {"version": 2},
        {"user_id": str(uuid4())},
        {"provider": "serper"},
        {"keyword_id": str(uuid4())},
    ],
)
def test_payload_rejects_overrides(extra):
    with pytest.raises(ValidationError):
        TaskPayload.model_validate({"job_id": str(uuid4()), **extra})


@pytest.mark.parametrize(
    "frequency,timezone,now,expected",
    [
        (
            "daily",
            "Asia/Ho_Chi_Minh",
            "2026-09-12T01:00:00+00:00",
            "2026-09-13T00:00:00+00:00",
        ),
        ("weekly", "UTC", "2026-09-12T01:00:00+00:00", "2026-09-14T07:00:00+00:00"),
    ],
)
def test_next_run(frequency, timezone, now, expected):
    assert (
        next_run(datetime.fromisoformat(now), frequency, "07:00", timezone).isoformat()
        == expected
    )


def test_dst_and_schedule_validation():
    assert (
        next_run(
            datetime(2026, 3, 8, 5, tzinfo=UTC), "daily", "02:30", "America/New_York"
        ).hour
        == 7
    )
    assert (
        next_run(
            datetime(2026, 11, 1, 4, tzinfo=UTC), "daily", "01:30", "America/New_York"
        ).hour
        == 5
    )
    for fields in [
        {"timezone": "invalid/timezone"},
        {"local_time": "25:00"},
        {"frequency": "* * * * *"},
        {"weekday": 7},
    ]:
        with pytest.raises(ValidationError):
            ScheduleRequest.model_validate(
                {
                    "timezone": "UTC",
                    "local_time": "07:00",
                    "frequency": "daily",
                    **fields,
                }
            )


async def test_worker_authentication_and_payload(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    import app.worker_main as module
    from app.worker_main import create_worker_app

    app = create_worker_app(cloud_settings(settings))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://worker"
    ) as client:
        assert (
            await client.post(
                "/internal/tasks/rank-check", json={"job_id": str(uuid4())}
            )
        ).status_code == 401
        monkeypatch.setattr(
            module,
            "verify_oauth2_token",
            lambda *args: {"email": "wrong@example.com", "email_verified": True},
        )
        assert (
            await client.post(
                "/internal/schedules/dispatch",
                headers={"Authorization": "Bearer invalid"},
            )
        ).status_code == 403
        monkeypatch.setattr(
            module,
            "verify_oauth2_token",
            lambda *args: {
                "email": "tasks@test.iam.gserviceaccount.com",
                "email_verified": True,
            },
        )
        # Reject task caller on scheduler endpoint, even with a valid signature.
        assert (
            await client.post(
                "/internal/schedules/dispatch",
                headers={"Authorization": "Bearer valid"},
            )
        ).status_code == 403
        assert (await client.get("/api/v1/projects")).status_code == 404


def test_production_rejects_local_queue(settings: Settings):
    configured = settings.model_dump()
    configured.update(
        app_env="production",
        debug=False,
        auth_cookie_secure=True,
        jwt_secret_key="random-production-729dF3xL56qC0rU4bTV",
        serp_provider="serpapi",
        serp_enabled_providers="serpapi",
        serpapi_api_key="mock",
    )
    with pytest.raises(ValidationError, match="Production requires Cloud Tasks"):
        Settings.model_validate(configured)


async def test_permanent_enqueue_error_is_safe_and_compensatable(settings: Settings):
    from google.api_core.exceptions import PermissionDenied

    client = Mock()
    client.create_task.side_effect = PermissionDenied("private SDK credentials")
    queue = CloudTasksRankCheckQueue(cloud_settings(settings), client)
    with pytest.raises(TaskQueueError) as error:
        await queue.enqueue_rank_check_job(uuid4())
    assert error.value.permanent
    assert str(error.value) == "TASK_ENQUEUE_FAILED"
