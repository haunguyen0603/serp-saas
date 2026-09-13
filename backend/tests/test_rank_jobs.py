import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_provider_attempt import RankCheckProviderAttempt
from app.models.rank_job import ProjectRankSchedule, RankCheckBatch, RankCheckJob
from app.services.rank_batches import RankBatchService
from app.services.rank_schedules import RankScheduleService
from app.services.rank_worker import RankCheckWorker
from app.services.serp import SerpProviderError
from app.services.serp.fake import FakeSerpProvider
from app.services.task_queue import TaskQueueError
from app.services.task_queue.local import LocalTaskQueue
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client
from tests.test_provider_routing import registration, use_router

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def setup(
    client: AsyncClient,
    app: FastAPI,
    count: int = 1,
    provider: FakeSerpProvider | None = None,
):
    account = await register(client)
    headers = authorization(account)
    user = UUID(account.json()["user"]["id"])
    project = project_body(
        await create_project(
            client, headers, keywords=[f"word {i}" for i in range(count)]
        )
    )
    project_id = UUID(project["id"])
    provider = provider or FakeSerpProvider()
    router = use_router(app, [registration(provider)])
    batches = RankBatchService(
        app.state.session_factory, app.state.settings, LocalTaskQueue()
    )
    worker = RankCheckWorker(batches, router)
    return headers, user, project_id, provider, batches, worker


async def test_api_queues_without_provider_and_worker_duplicate_delivery(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, user, project, provider, batches, worker = await setup(
        auth_client, auth_app
    )
    response = await auth_client.post(
        f"/api/v1/projects/{project}/rank-check-batches", headers=headers, json={}
    )
    assert response.status_code == 202
    assert provider.requests == []
    accepted = response.json()
    job = UUID(accepted["job_id"])
    assert await worker.execute(job)
    assert await worker.execute(job)
    assert len(provider.requests) == 1
    detail = await batches.detail(project, user, UUID(accepted["batch_id"]))
    assert detail.status == "completed" and detail.progress_percent == 100
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankCheck)) == 1


async def test_racing_workers_exact_counters_and_single_claim(
    auth_client: AsyncClient, auth_app: FastAPI
):
    _, user, project, provider, batches, worker = await setup(
        auth_client, auth_app, 12, FakeSerpProvider(delay_seconds=0.05)
    )
    batch = await batches.create(project, user)
    await worker.recover(limit=100)
    async with auth_app.state.session_factory() as session:
        ids = list(await session.scalars(select(RankCheckJob.id)))
    await asyncio.gather(*(worker.execute(job) for job in ids + ids))
    detail = await batches.detail(project, user, batch.batch_id)
    assert detail.succeeded_keyword_count == 12
    assert detail.failed_keyword_count == detail.running_keyword_count == 0
    assert detail.status == "completed"
    assert len(provider.requests) == 12


async def test_retry_reuses_check_and_preserves_attempt_history(
    auth_client: AsyncClient, auth_app: FastAPI
):
    provider = FakeSerpProvider()
    provider.add_error(
        "word 0", SerpProviderError("SERP_PROVIDER_TIMEOUT", "Timed out")
    )
    _, user, project, _, batches, worker = await setup(
        auth_client, auth_app, provider=provider
    )
    batch = await batches.create(project, user)
    assert not await worker.execute(batch.job_id)
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, batch.job_id)
        check_id = job.rank_check_id
        job.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
    worker.provider = use_router(auth_app, [registration(FakeSerpProvider())])
    assert await worker.execute(batch.job_id)
    async with auth_app.state.session_factory() as session:
        job = await session.get(RankCheckJob, batch.job_id)
        assert job.rank_check_id == check_id and job.attempt_count == 2
        check = await session.get(RankCheck, check_id)
        assert (
            check.status == RankCheckStatus.SUCCEEDED
            and check.provider_request_count == 2
        )
        attempts = list(
            await session.scalars(
                select(RankCheckProviderAttempt).order_by(
                    RankCheckProviderAttempt.attempt_number
                )
            )
        )
        assert [a.attempt_number for a in attempts] == [1, 2]
        assert await session.scalar(select(func.count()).select_from(RankCheck)) == 1


async def test_cancel_and_archival_skip_provider(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, user, project, provider, batches, worker = await setup(
        auth_client, auth_app
    )
    first = await batches.create(project, user)
    await batches.cancel(project, user, first.batch_id)
    assert await worker.execute(first.job_id)
    assert (await batches.detail(project, user, first.batch_id)).status == "cancelled"
    second = await batches.create(project, user)
    await auth_client.patch(
        f"/api/v1/projects/{project}", headers=headers, json={"status": "archived"}
    )
    assert await worker.execute(second.job_id)
    assert (
        await batches.detail(project, user, second.batch_id)
    ).status == "completed_with_errors"
    assert provider.requests == []


async def test_crash_after_success_reconciles_without_provider(
    auth_client: AsyncClient, auth_app: FastAPI
):
    _, user, project, provider, batches, worker = await setup(auth_client, auth_app)
    batch = await batches.create(project, user)
    assert await worker.execute(batch.job_id)
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, batch.job_id)
        job.status = "running"
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        job.completed_at = None
    assert await worker.execute(batch.job_id)
    assert len(provider.requests) == 1
    assert (await batches.detail(project, user, batch.batch_id)).status == "completed"


async def test_pending_enqueue_failure_recovery(
    auth_client: AsyncClient, auth_app: FastAPI
):
    _, user, project, _, batches, worker = await setup(auth_client, auth_app)

    class BrokenQueue:
        async def enqueue_rank_check_job(self, *args, **kwargs):
            raise TaskQueueError("TASK_ENQUEUE_FAILED")

    batches.queue = BrokenQueue()
    batch = await batches.create(project, user)
    assert batch.status == "pending"
    batches.queue = LocalTaskQueue()
    await worker.recover(local=True)
    assert (await batches.detail(project, user, batch.batch_id)).status == "completed"


async def test_schedule_overlap_catchup_and_delete_preserves_history(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, user, project, _, batches, worker = await setup(auth_client, auth_app)
    from datetime import timedelta

    from app.models.project import Project
    from app.services.billing.subscriptions import SubscriptionService

    async with auth_app.state.session_factory() as session, session.begin():
        owner = (await session.get(Project, project)).user_id
        await SubscriptionService(session).activate(
            owner,
            owner,
            "desktop_pro",
            datetime.now(UTC),
            datetime.now(UTC) + timedelta(days=90),
            "manual_bank_transfer",
            "fixture",
            None,
        )
    url = f"/api/v1/projects/{project}/rank-schedule"
    response = await auth_client.put(
        url,
        headers=headers,
        json={
            "frequency": "daily",
            "local_time": "07:00",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    assert response.status_code == 200
    async with auth_app.state.session_factory() as session, session.begin():
        schedule = await session.scalar(select(ProjectRankSchedule))
        schedule.next_run_at = datetime.now(UTC) - timedelta(days=30)
    service = RankScheduleService(batches)
    assert sum(await asyncio.gather(service.dispatch(), service.dispatch())) == 1
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(RankCheckBatch)) == 1
        )
        assert (
            await session.scalar(select(ProjectRankSchedule))
        ).next_run_at > datetime.now(UTC)
    await worker.recover(local=True)
    assert (await auth_client.delete(url, headers=headers)).status_code == 204
    async with auth_app.state.session_factory() as session:
        batch = await session.scalar(select(RankCheckBatch))
        assert batch.schedule_id is None and batch.trigger_type == "scheduled"
        assert batch.status == "completed"


async def test_tenant_isolation_pagination_and_history_protection(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, user, project, _, batches, _ = await setup(auth_client, auth_app)
    one = await batches.create(project, user)
    await batches.create(project, user)
    other = authorization(await register(auth_client))
    root = f"/api/v1/projects/{project}"
    for path in [
        "rank-check-batches",
        f"rank-check-batches/{one.batch_id}",
        f"rank-check-batches/{one.batch_id}/jobs",
        "rank-schedule",
    ]:
        assert (
            await auth_client.get(f"{root}/{path}", headers=other)
        ).status_code == 404
    assert (
        await auth_client.post(
            f"{root}/rank-check-batches/{one.batch_id}/cancel", headers=other
        )
    ).status_code == 404
    assert (await auth_client.delete(root, headers=headers)).status_code == 409
    page = await batches.history(project, user, 1, None)
    assert page.has_more
    next_page = await batches.history(project, user, 1, page.next_cursor)
    assert page.items[0].id != next_page.items[0].id


async def test_max_attempts_and_expired_claim(
    auth_client: AsyncClient, auth_app: FastAPI
):
    _, user, project, provider, batches, worker = await setup(auth_client, auth_app)
    batch = await batches.create(project, user)
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, batch.job_id)
        job.status, job.attempt_count = "running", 1
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert await worker.execute(batch.job_id)
    assert len(provider.requests) == 1
    second = await batches.create(project, user)
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, second.job_id)
        job.attempt_count = job.max_attempts
    assert await worker.execute(second.job_id)
    assert len(provider.requests) == 1
    assert (
        await batches.detail(project, user, second.batch_id)
    ).failed_keyword_count == 1


async def test_late_worker_cannot_persist_after_lease_reclaim(
    auth_client: AsyncClient, auth_app: FastAPI
):
    provider = FakeSerpProvider(delay_seconds=0.3)
    _, user, project, _, batches, first_worker = await setup(
        auth_client, auth_app, provider=provider
    )
    batch = await batches.create(project, user)
    old = asyncio.create_task(first_worker.execute(batch.job_id))
    # Wait for durable linkage, then simulate the old instance losing its lease.
    for _ in range(100):
        async with auth_app.state.session_factory() as session:
            job = await session.get(RankCheckJob, batch.job_id)
            ready = job.rank_check_id is not None
        if ready:
            break
        await asyncio.sleep(0.005)
    assert ready
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, batch.job_id)
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    new_worker = RankCheckWorker(
        batches, use_router(auth_app, [registration(FakeSerpProvider())])
    )
    assert await new_worker.execute(batch.job_id)
    assert not await old
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankCheck)) == 1
        assert (
            await session.scalar(select(RankCheck))
        ).status == RankCheckStatus.SUCCEEDED
    assert (
        await batches.detail(project, user, batch.batch_id)
    ).succeeded_keyword_count == 1


async def test_batch_validation_large_projects_and_single_keyword(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, user, project, provider, batches, _ = await setup(
        auth_client, auth_app, 26
    )
    root = f"/api/v1/projects/{project}"
    response = await auth_client.post(
        f"{root}/rank-check-batches", headers=headers, json={}
    )
    assert (
        response.status_code == 202 and response.json()["requested_keyword_count"] == 26
    )
    assert provider.requests == []
    keywords = (await auth_client.get(f"{root}/keywords", headers=headers)).json()[
        "items"
    ]
    selected = await auth_client.post(
        f"{root}/keywords/{keywords[0]['id']}/rank-check-batches",
        headers=headers,
        json={},
    )
    assert selected.status_code == 202 and selected.json()["job_id"]
    for body in [{"provider": "serper"}, {"user_id": str(user)}, {"keyword_ids": []}]:
        assert (
            await auth_client.post(
                f"{root}/rank-check-batches", headers=headers, json=body
            )
        ).status_code in (400, 422)
    batches.settings = batches.settings.model_copy(
        update={"rank_check_batch_max_keywords": 2}
    )
    from app.core.errors import AppError

    with pytest.raises(AppError, match="Too many"):
        await batches.create(project, user)


async def test_schedule_disabled_empty_and_archived(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, _, project, provider, batches, _ = await setup(auth_client, auth_app)
    root = f"/api/v1/projects/{project}"
    schedule_body = {
        "enabled": False,
        "frequency": "weekly",
        "weekday": 3,
        "local_time": "07:00",
        "timezone": "UTC",
    }
    assert (
        await auth_client.put(
            f"{root}/rank-schedule", headers=headers, json=schedule_body
        )
    ).status_code == 200
    async with auth_app.state.session_factory() as session, session.begin():
        schedule = await session.scalar(select(ProjectRankSchedule))
        schedule.next_run_at = datetime.now(UTC) - timedelta(days=1)
    service = RankScheduleService(batches)
    assert await service.dispatch() == 0
    async with auth_app.state.session_factory() as session, session.begin():
        schedule = await session.scalar(select(ProjectRankSchedule))
        schedule.enabled = True
    await auth_client.patch(root, headers=headers, json={"status": "archived"})
    assert await service.dispatch() == 0
    async with auth_app.state.session_factory() as session:
        assert not (await session.scalar(select(ProjectRankSchedule))).enabled
    assert not provider.requests


async def test_worker_http_retry_terminal_and_payload_contract(
    auth_client: AsyncClient, auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    from httpx import ASGITransport

    import app.worker_main as module

    provider = FakeSerpProvider()
    provider.add_error(
        "word 0", SerpProviderError("SERP_PROVIDER_TIMEOUT", "Temporary")
    )
    _, user, project, _, batches, worker = await setup(
        auth_client, auth_app, provider=provider
    )
    app = module.create_worker_app(auth_app.state.settings)
    app.state.session_factory = auth_app.state.session_factory
    monkeypatch.setattr(module, "get_provider_router", lambda *args: worker.provider)
    retry = await batches.create(project, user)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://worker"
    ) as client:
        payload = {"version": 1, "job_id": str(retry.job_id)}
        for _ in range(2):
            response = await client.post("/internal/tasks/rank-check", json=payload)
            assert response.status_code == 503 and response.json() == {
                "status": "retry"
            }
        assert len(provider.requests) == 1  # backoff delivery does not claim again
        await batches.cancel(project, user, retry.batch_id)
        assert (
            await client.post("/internal/tasks/rank-check", json=payload)
        ).status_code == 200
        assert len(provider.requests) == 1
        terminal_provider = FakeSerpProvider()
        terminal_provider.add_error(
            "word 0", SerpProviderError("SERP_PROVIDER_AUTH_ERROR", "Unavailable")
        )
        worker.provider = use_router(auth_app, [registration(terminal_provider)])
        terminal = await batches.create(project, user)
        terminal_payload = {"version": 1, "job_id": str(terminal.job_id)}
        for _ in range(2):
            assert (
                await client.post("/internal/tasks/rank-check", json=terminal_payload)
            ).status_code == 200
        assert (
            await batches.detail(project, user, terminal.batch_id)
        ).failed_keyword_count == 1
        assert len(terminal_provider.requests) == 1
        for invalid in [{**payload, "provider": "serper"}, {**payload, "version": 2}]:
            assert (
                await client.post("/internal/tasks/rank-check", json=invalid)
            ).status_code == 422


async def test_not_due_and_empty_project_schedule_are_safe(
    auth_client: AsyncClient, auth_app: FastAPI
):
    headers, _, project, provider, batches, _ = await setup(auth_client, auth_app)
    from datetime import timedelta

    from app.models.project import Project
    from app.services.billing.subscriptions import SubscriptionService

    async with auth_app.state.session_factory() as session, session.begin():
        owner = (await session.get(Project, project)).user_id
        await SubscriptionService(session).activate(
            owner,
            owner,
            "desktop_pro",
            datetime.now(UTC),
            datetime.now(UTC) + timedelta(days=90),
            "manual_bank_transfer",
            "fixture",
            None,
        )
    root = f"/api/v1/projects/{project}"
    response = await auth_client.put(
        f"{root}/rank-schedule",
        headers=headers,
        json={"frequency": "daily", "local_time": "07:00", "timezone": "UTC"},
    )
    assert response.status_code == 200
    service = RankScheduleService(batches)
    assert await service.dispatch() == 0
    keywords = (await auth_client.get(f"{root}/keywords", headers=headers)).json()[
        "items"
    ]
    await auth_client.patch(
        f"{root}/keywords/{keywords[0]['id']}", headers=headers, json={"active": False}
    )
    async with auth_app.state.session_factory() as session, session.begin():
        schedule = await session.scalar(select(ProjectRankSchedule))
        schedule.next_run_at = datetime.now(UTC) - timedelta(days=30)
    assert await service.dispatch() == 0
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(select(ProjectRankSchedule))
        ).next_run_at > datetime.now(UTC)
        assert (
            await session.scalar(select(func.count()).select_from(RankCheckBatch)) == 0
        )
    assert provider.requests == []
