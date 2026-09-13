import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select, update

from app.core.errors import AppError
from app.models.billing import (
    BillingAuditEvent,
    Plan,
    Subscription,
    UsageEvent,
    UsagePeriod,
)
from app.models.keyword import Keyword
from app.models.rank_job import ProjectRankSchedule, RankCheckBatch, RankCheckJob
from app.models.user import User
from app.services.billing.reconciliation import reconcile_subscriptions
from app.services.billing.subscriptions import SubscriptionService, add_months
from app.services.billing.usage import UsageService
from app.services.rank_schedules import RankScheduleService
from app.services.task_queue import TaskQueueError
from tests.business_helpers import authorization, create_project, register
from tests.test_auth import auth_app, auth_client
from tests.test_rank_jobs import setup

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def admin_setup(client, app):
    admin = await register(client, "admin")
    actor = UUID(admin.json()["user"]["id"])
    async with app.state.session_factory() as session, session.begin():
        (await session.get(User, actor)).is_platform_admin = True
    account = await register(client, "customer")
    return (
        authorization(admin),
        authorization(account),
        UUID(account.json()["user"]["id"]),
    )


async def activate(client, headers, user, code="desktop_starter", **changes):
    return await client.post(
        f"/api/v1/admin/customers/{user}/subscriptions",
        headers=headers,
        json={
            "plan_code": code,
            "period_start": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
            "period_end": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
            "payment_method": "manual_bank_transfer",
            "payment_reference": "BANK-<safe>",
            "note": "internal-private-note",
            **changes,
        },
    )


async def test_catalog_free_and_security(auth_client, auth_app):
    admin, user, uid = await admin_setup(auth_client, auth_app)
    plans = (await auth_client.get("/api/v1/billing/plans")).json()
    assert [
        (
            p["code"],
            p["price_monthly_minor_units"],
            p["max_projects"],
            p["max_keywords"],
            p["monthly_keyword_checks"],
        )
        for p in plans
    ] == [
        ("desktop_free", 0, 1, 50, 100),
        ("desktop_starter", 1900, 5, 500, 5000),
        ("desktop_pro", 12900, 20, 5000, 50000),
        ("mobile_free", 0, 1, 20, 50),
        ("mobile_starter", 3900, 3, 200, 1000),
        ("mobile_pro", 24900, 10, 1000, 10000),
    ]
    me = (await auth_client.get("/api/v1/billing/me", headers=user)).json()
    assert [d["plan"]["code"] for d in me["devices"]] == ["desktop_free", "mobile_free"]
    for method, path, body in [
        ("GET", f"/admin/customers/{uid}/billing", None),
        ("GET", "/admin/customers", None),
        ("POST", f"/admin/customers/{uid}/subscriptions", {}),
        (
            "POST",
            f"/admin/customers/{uid}/usage-adjustments",
            {"device_scope": "desktop", "amount": 500, "note": "forged"},
        ),
    ]:
        response = await auth_client.request(
            method, "/api/v1" + path, headers=user, json=body
        )
        assert (
            response.status_code == 403
            and response.json()["error"]["code"] == "ADMIN_REQUIRED"
        )
    assert (
        await auth_client.get(f"/api/v1/billing/{uid}", headers=user)
    ).status_code == 404
    assert (await activate(auth_client, admin, uid)).status_code == 201
    for path in ["/billing/me", "/billing/me/usage"]:
        response = await auth_client.get("/api/v1" + path, headers=user)
        assert (
            "internal-private-note" not in response.text
            and "BANK-" not in response.text
        )
    assert (
        await activate(auth_client, admin, uid, device_scope="mobile")
    ).status_code == 422
    async with auth_app.state.session_factory() as session, session.begin():
        await session.execute(
            update(Plan).where(Plan.code == "mobile_pro").values(active=False)
        )
    assert (await activate(auth_client, admin, uid, "mobile_pro")).json()["error"][
        "code"
    ] == "PLAN_NOT_FOUND"


async def test_transitions_snapshots_extension_and_device_independence(
    auth_client, auth_app
):
    admin, user, uid = await admin_setup(auth_client, auth_app)
    first = (await activate(auth_client, admin, uid)).json()
    mobile = (await activate(auth_client, admin, uid, "mobile_starter")).json()
    assert (await activate(auth_client, admin, uid)).status_code == 409
    async with auth_app.state.session_factory() as session, session.begin():
        period = await UsageService(session).reserve(uid, "desktop", 7)
        period_id = period.id
        await session.execute(
            update(Plan).where(Plan.code == "desktop_starter").values(max_projects=77)
        )
    extension = await auth_client.post(
        f"/api/v1/admin/customers/{uid}/subscriptions/{first['id']}/extend",
        headers=admin,
        json={"period_end": (datetime.now(UTC) + timedelta(days=120)).isoformat()},
    )
    assert (
        extension.status_code == 200
        and extension.json()["snapshot"]["max_projects"] == 5
    )
    me = (await auth_client.get("/api/v1/billing/me", headers=user)).json()
    assert (
        me["devices"][0]["usage"]["id"] == str(period_id)
        and me["devices"][0]["usage"]["reserved"] == 7
    )
    upgrade = await activate(
        auth_client, admin, uid, "desktop_pro", replace_existing=True
    )
    assert upgrade.status_code == 201
    me = (await auth_client.get("/api/v1/billing/me", headers=user)).json()
    assert me["devices"][0]["usage"]["remaining"] == 50000
    assert me["devices"][1]["subscription_id"] == mobile["id"]
    cancel = await auth_client.post(
        f"/api/v1/admin/customers/{uid}/subscriptions/{upgrade.json()['id']}/cancel",
        headers=admin,
    )
    assert cancel.status_code == 200
    history = (
        await auth_client.get(
            f"/api/v1/admin/customers/{uid}/subscriptions", headers=admin
        )
    ).json()
    assert len(history) >= 6 and any(
        s["payment_reference"] == "BANK-<safe>" for s in history
    )
    other = UUID((await register(auth_client)).json()["user"]["id"])
    assert (
        await auth_client.post(
            f"/api/v1/admin/customers/{other}/subscriptions/{first['id']}/cancel",
            headers=admin,
        )
    ).status_code == 404


async def test_activation_race_and_scheduled_expiry(auth_client, auth_app):
    admin, user, uid = await admin_setup(auth_client, auth_app)
    results = await asyncio.gather(
        *(activate(auth_client, admin, uid) for _ in range(2))
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    current = next(r.json() for r in results if r.status_code == 201)
    start = datetime.fromisoformat(current["period_end"])
    scheduled = await activate(
        auth_client,
        admin,
        uid,
        "desktop_free",
        period_start=start.isoformat(),
        period_end=(start + timedelta(days=40)).isoformat(),
        payment_method=None,
    )
    assert scheduled.status_code == 201 and scheduled.json()["status"] == "scheduled"
    async with auth_app.state.session_factory() as session, session.begin():
        await reconcile_subscriptions(session, start + timedelta(seconds=1))
        active = list(
            await session.scalars(
                select(Subscription).where(
                    Subscription.user_id == uid, Subscription.status == "active"
                )
            )
        )
        assert len(active) == 2 and {s.snapshot["code"] for s in active} == {
            "desktop_free",
            "mobile_free",
        }
        await reconcile_subscriptions(session, start + timedelta(days=41))
        assert (
            await SubscriptionService(session).resolve(
                uid, "desktop", start + timedelta(days=41)
            )
        ).snapshot["code"] == "desktop_free"


@pytest.mark.parametrize("device,limit", [("desktop", 50), ("mobile", 20)])
async def test_resources_bulk_reactivation_and_device_change(
    auth_client, auth_app, device, limit
):
    account = await register(auth_client)
    headers = authorization(account)
    result = await create_project(
        auth_client, headers, device=device, keywords=[f"k{i}" for i in range(limit)]
    )
    assert result.status_code == 201
    project = result.json()["project"]["id"]
    assert (await create_project(auth_client, headers, device=device)).json()["error"][
        "code"
    ] == "PROJECT_LIMIT_EXCEEDED"
    bulk = await auth_client.post(
        f"/api/v1/projects/{project}/keywords/bulk",
        headers=headers,
        json={"keywords": ["extra", "other"]},
    )
    assert bulk.status_code == 409
    items = (
        await auth_client.get(f"/api/v1/projects/{project}/keywords", headers=headers)
    ).json()["items"]
    first = items[0]["id"]
    assert (
        await auth_client.patch(
            f"/api/v1/projects/{project}/keywords/{first}",
            headers=headers,
            json={"active": False},
        )
    ).status_code == 200
    assert (
        await auth_client.post(
            f"/api/v1/projects/{project}/keywords",
            headers=headers,
            json={"keyword": "replacement"},
        )
    ).status_code == 201
    assert (
        await auth_client.patch(
            f"/api/v1/projects/{project}/keywords/{first}",
            headers=headers,
            json={"active": True},
        )
    ).json()["error"]["code"] == "KEYWORD_LIMIT_EXCEEDED"
    other = "mobile" if device == "desktop" else "desktop"
    other_project = await create_project(auth_client, headers, device=other)
    assert other_project.status_code == 201
    assert (
        await auth_client.patch(
            f"/api/v1/projects/{project}", headers=headers, json={"device": other}
        )
    ).status_code == 409
    assert (
        await auth_client.get(f"/api/v1/projects/{project}/keywords", headers=headers)
    ).json()["items"]


async def test_atomic_reservation_race_and_reset_adjustment(auth_client, auth_app):
    admin, user, uid = await admin_setup(auth_client, auth_app)

    async def reserve():
        try:
            async with auth_app.state.session_factory() as session, session.begin():
                await UsageService(session).reserve(uid, "desktop", 80)
            return True
        except AppError as error:
            assert error.code == "USAGE_LIMIT_EXCEEDED"
            return False

    assert sorted(await asyncio.gather(reserve(), reserve())) == [False, True]
    adjusted = await auth_client.post(
        f"/api/v1/admin/customers/{uid}/usage-adjustments",
        headers=admin,
        json={"device_scope": "desktop", "amount": 500, "note": "goodwill"},
    )
    assert adjusted.json()["devices"][0]["usage"]["remaining"] == 520
    async with auth_app.state.session_factory() as session, session.begin():
        sub = await SubscriptionService(session).resolve(uid, "desktop")
        now = add_months(sub.period_start, 1) + timedelta(seconds=1)
        period = await SubscriptionService(session).period(sub, now)
        assert (
            period.reserved_keyword_checks
            == period.committed_keyword_checks
            == period.adjustment
            == 0
        )
    assert add_months(datetime(2026, 1, 31, tzinfo=UTC), 1).day == 28
    assert add_months(datetime(2026, 1, 31, tzinfo=UTC), 2).day == 31


async def test_m5_partial_cancel_replay_and_compensation(auth_client, auth_app):
    headers, uid, project, provider, batches, worker = await setup(
        auth_client, auth_app, 3
    )
    batch = await batches.create(project, uid)
    async with auth_app.state.session_factory() as session:
        jobs = list(await session.scalars(select(RankCheckJob.id)))
        period = await session.scalar(select(UsagePeriod))
        assert (
            period.reserved_keyword_checks == 3 and period.committed_keyword_checks == 0
        )
    assert await worker.execute(jobs[0])
    assert await worker.execute(jobs[0])
    await batches.cancel(project, uid, batch.batch_id)
    for job in jobs:
        assert await worker.execute(job)
    async with auth_app.state.session_factory() as session:
        period = await session.scalar(select(UsagePeriod))
        assert (
            period.reserved_keyword_checks == 0 and period.committed_keyword_checks == 1
        )
        assert await session.scalar(select(func.count()).select_from(UsageEvent)) == 3
    assert len(provider.requests) == 1

    class Broken:
        async def enqueue_rank_check_job(self, *args, **kwargs):
            raise TaskQueueError("permanent", permanent=True)

    batches.queue = Broken()
    failed = await batches.create(project, uid)
    assert failed.status == "completed_with_errors"
    async with auth_app.state.session_factory() as session:
        assert (await session.scalar(select(UsagePeriod))).reserved_keyword_checks == 0


async def test_schedule_limits_downgrade_and_no_partial_batch(auth_client, auth_app):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    project = (
        await create_project(auth_client, headers, keywords=["one", "two"])
    ).json()["project"]["id"]
    url = f"/api/v1/projects/{project}/rank-schedule"
    body = {"frequency": "daily", "local_time": "07:00", "timezone": "UTC"}
    assert (await auth_client.put(url, headers=headers, json=body)).json()["error"][
        "code"
    ] == "SCHEDULE_NOT_INCLUDED"
    assert (await activate(auth_client, admin, uid)).status_code == 201
    assert (await auth_client.put(url, headers=headers, json=body)).json()["error"][
        "code"
    ] == "SCHEDULE_FREQUENCY_NOT_ALLOWED"
    assert (
        await auth_client.put(
            url, headers=headers, json={**body, "frequency": "weekly"}
        )
    ).status_code == 200
    assert (
        await activate(auth_client, admin, uid, "desktop_pro", replace_existing=True)
    ).status_code == 201
    assert (await auth_client.put(url, headers=headers, json=body)).status_code == 200
    assert (
        await activate(auth_client, admin, uid, replace_existing=True)
    ).status_code == 201
    assert not (await auth_client.get(url, headers=headers)).json()["enabled"]
    assert (
        await auth_client.put(
            url, headers=headers, json={**body, "frequency": "weekly"}
        )
    ).status_code == 200
    from app.services.rank_batches import RankBatchService
    from app.services.task_queue.local import LocalTaskQueue

    batches = RankBatchService(
        auth_app.state.session_factory, auth_app.state.settings, LocalTaskQueue()
    )
    async with auth_app.state.session_factory() as session, session.begin():
        await UsageService(session).adjust(uid, uid, "desktop", -4999, "test")
        schedule = await session.scalar(select(ProjectRankSchedule))
        schedule.next_run_at = datetime.now(UTC) - timedelta(days=1)
    assert await RankScheduleService(batches).dispatch() == 0
    assert await RankScheduleService(batches).dispatch() == 0
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(RankCheckBatch)) == 0
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(BillingAuditEvent)
                .where(BillingAuditEvent.event_type == "schedule_disabled_due_to_plan")
            )
            >= 1
        )


async def test_fallback_and_retry_count_one_logical_check(auth_client, auth_app):
    from app.services.serp import SerpProviderError
    from app.services.serp.fake import FakeSerpProvider
    from tests.test_provider_routing import registration, use_router

    headers, uid, project, _, batches, worker = await setup(auth_client, auth_app)
    first = FakeSerpProvider(name="first")
    first.add_error("word 0", SerpProviderError("SERP_PROVIDER_TIMEOUT", "Timeout"))
    second = FakeSerpProvider(name="second")
    worker.provider = use_router(auth_app, [registration(first), registration(second)])
    accepted = await batches.create(project, uid)
    assert await worker.execute(accepted.job_id)
    assert await worker.execute(accepted.job_id)
    assert len(first.requests) == len(second.requests) == 1
    async with auth_app.state.session_factory() as session:
        assert (await session.scalar(select(UsagePeriod))).committed_keyword_checks == 1
        assert await session.scalar(select(func.count()).select_from(UsageEvent)) == 1


async def test_no_quota_no_batch_and_forged_unreserved_job(auth_client, auth_app):
    headers, uid, project, provider, batches, worker = await setup(
        auth_client, auth_app
    )
    async with auth_app.state.session_factory() as session, session.begin():
        await UsageService(session).adjust(uid, uid, "desktop", -100, "exhausted")
    response = await auth_client.post(
        f"/api/v1/projects/{project}/rank-check-batches", headers=headers, json={}
    )
    assert response.status_code == 409
    assert response.json()["error"]["remaining"] == 0
    async with auth_app.state.session_factory() as session, session.begin():
        assert (
            await session.scalar(select(func.count()).select_from(RankCheckBatch)) == 0
        )
        batch = RankCheckBatch(
            user_id=uid,
            project_id=project,
            trigger_type="manual_project",
            requested_keyword_count=1,
        )
        session.add(batch)
        await session.flush()
        keyword = await session.scalar(select(Keyword))
        job = RankCheckJob(
            user_id=uid,
            project_id=project,
            keyword_id=keyword.id,
            batch_id=batch.id,
            max_attempts=5,
        )
        session.add(job)
        await session.flush()
        job_id = job.id
    assert await worker.execute(job_id)
    assert provider.requests == []


async def test_manual_scheduled_race_reserves_only_one_full_batch(
    auth_client, auth_app
):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    assert (await activate(auth_client, admin, uid)).status_code == 201
    project = UUID(
        (await create_project(auth_client, headers, keywords=["one", "two"])).json()[
            "project"
        ]["id"]
    )
    assert (
        await auth_client.put(
            f"/api/v1/projects/{project}/rank-schedule",
            headers=headers,
            json={"frequency": "weekly", "local_time": "07:00", "timezone": "UTC"},
        )
    ).status_code == 200
    from app.services.rank_batches import RankBatchService
    from app.services.task_queue.local import LocalTaskQueue

    batches = RankBatchService(
        auth_app.state.session_factory, auth_app.state.settings, LocalTaskQueue()
    )
    async with auth_app.state.session_factory() as session, session.begin():
        await UsageService(session).adjust(uid, uid, "desktop", -4998, "race budget")
        (await session.scalar(select(ProjectRankSchedule))).next_run_at = datetime.now(
            UTC
        ) - timedelta(days=1)

    async def manual():
        try:
            await batches.create(project, uid)
        except AppError as exc:
            assert exc.code == "USAGE_LIMIT_EXCEEDED"

    await asyncio.gather(manual(), RankScheduleService(batches).dispatch())
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(RankCheckBatch)) == 1
        )
        periods = list(
            await session.scalars(
                select(UsagePeriod).where(UsagePeriod.device_scope == "desktop")
            )
        )
        assert sum(p.reserved_keyword_checks for p in periods) == 2


async def test_downgrade_preserves_over_limit_and_blocks_expansion(
    auth_client, auth_app
):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    assert (await activate(auth_client, admin, uid)).status_code == 201
    for i in range(2):
        assert (
            await create_project(
                auth_client,
                headers,
                name=f"p{i}",
                keywords=[f"k{j}" for j in range(30)],
            )
        ).status_code == 201
    assert (
        await activate(
            auth_client,
            admin,
            uid,
            "desktop_free",
            payment_method=None,
            replace_existing=True,
        )
    ).status_code == 201
    me = (await auth_client.get("/api/v1/billing/me", headers=headers)).json()
    assert me["devices"][0]["over_limit"]
    assert (await create_project(auth_client, headers)).status_code == 409
    projects = (await auth_client.get("/api/v1/projects", headers=headers)).json()[
        "items"
    ]
    assert len(projects) == 2
    assert (
        await auth_client.post(
            f"/api/v1/projects/{projects[0]['id']}/keywords",
            headers=headers,
            json={"keyword": "new"},
        )
    ).status_code == 409
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Keyword)) == 60


async def test_customer_search_cursor_and_resource_race(auth_client, auth_app):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    first = (
        await auth_client.get("/api/v1/admin/customers?limit=1", headers=admin)
    ).json()
    assert first["has_more"]
    second = (
        await auth_client.get(
            "/api/v1/admin/customers",
            headers=admin,
            params={"limit": 1, "cursor": first["next_cursor"]},
        )
    ).json()
    assert first["items"][0]["user_id"] != second["items"][0]["user_id"]
    search = (
        await auth_client.get("/api/v1/admin/customers?search=customer-", headers=admin)
    ).json()
    assert len(search["items"]) == 1
    responses = await asyncio.gather(
        create_project(auth_client, headers), create_project(auth_client, headers)
    )
    assert sorted(r.status_code for r in responses) == [201, 409]


async def test_archived_job_and_stranded_enqueue_release(auth_client, auth_app):
    headers, uid, project, provider, batches, worker = await setup(
        auth_client, auth_app
    )
    first = await batches.create(project, uid)
    await auth_client.patch(
        f"/api/v1/projects/{project}", headers=headers, json={"status": "archived"}
    )
    assert await worker.execute(first.job_id)
    async with auth_app.state.session_factory() as session:
        period = await session.scalar(select(UsagePeriod))
        assert period.committed_keyword_checks == period.reserved_keyword_checks == 0
    assert not provider.requests
    await auth_client.patch(
        f"/api/v1/projects/{project}", headers=headers, json={"status": "active"}
    )

    class Broken:
        async def enqueue_rank_check_job(self, *args, **kwargs):
            raise TaskQueueError("temporary")

    batches.queue = Broken()
    second = await batches.create(project, uid)
    async with auth_app.state.session_factory() as session, session.begin():
        job = await session.get(RankCheckJob, second.job_id)
        job.created_at = datetime.now(UTC) - timedelta(days=30)
    await worker.recover(local=True)
    async with auth_app.state.session_factory() as session:
        assert (await session.scalar(select(UsagePeriod))).reserved_keyword_checks == 0


async def test_stale_project_read_cannot_bypass_reactivation_quota(
    auth_client, auth_app
):
    from app.services.billing.entitlements import EntitlementService

    account = await register(auth_client)
    uid = UUID(account.json()["user"]["id"])
    headers = authorization(account)
    result = await create_project(
        auth_client, headers, keywords=[f"k{i}" for i in range(50)]
    )
    project_id = UUID(result.json()["project"]["id"])
    await auth_client.patch(
        f"/api/v1/projects/{project_id}", headers=headers, json={"status": "archived"}
    )
    async with auth_app.state.session_factory() as stale, stale.begin():
        from app.models.project import Project

        old = await stale.get(Project, project_id)
        assert old.status == "archived"
        assert (
            await auth_client.patch(
                f"/api/v1/projects/{project_id}",
                headers=headers,
                json={"status": "active"},
            )
        ).status_code == 200
        with pytest.raises(AppError) as exc:
            await EntitlementService(stale).keyword_add(uid, project_id, ["new"])
        assert exc.value.code == "KEYWORD_LIMIT_EXCEEDED"
