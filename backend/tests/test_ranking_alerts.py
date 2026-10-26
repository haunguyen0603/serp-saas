import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, update

from app.models.project import Project
from app.models.rank_check import RankCheck
from app.models.ranking_alert import (
    RankingAlert,
    RankingAlertDelivery,
    RankingAlertEvaluation,
    RankingAlertPreference,
)
from app.models.user import User
from app.services.auth_email import AuthEmailError
from app.services.rank_checks import RankCheckExecutionService
from app.services.ranking_alert_email import AlertEmailWorker, RankingAlertEmailSender
from app.services.ranking_alerts import AlertEvaluationService, classify
from app.services.serp.base import SerpProviderError
from app.services.serp.factory import get_provider_router
from app.services.serp.types import OrganicResult
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]


def results(
    position: int | None, hostname: str = "www.alerts.example"
) -> list[OrganicResult]:
    return [
        OrganicResult(
            i,
            f"Result {i}",
            f"https://{hostname if i == position else f'other{i}.example'}/",
            hostname if i == position else f"other{i}.example",
        )
        for i in range(1, 11)
    ]


@pytest.mark.parametrize(
    "before,after,threshold,expected",
    [
        (None, 7, 3, "entered_top10"),
        (6, None, 3, "left_top10"),
        (9, 4, 3, "rank_improved"),
        (2, 6, 3, "rank_declined"),
        (6, 4, 3, None),
        (4, 4, 3, None),
        (None, None, 3, None),
        (6, 3, 3, "rank_improved"),
        (3, 6, 3, "rank_declined"),
        (6, 4, 2, "rank_improved"),
    ],
)
def test_classification(before, after, threshold, expected):
    assert classify(before, after, threshold) == expected


async def setup(client: AsyncClient, app: FastAPI):
    account = await register(client, "alerts")
    headers = authorization(account)
    uid = UUID(account.json()["user"]["id"])
    site = (
        await client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={"name": "Alert site", "primary_domain": "alerts.example"},
        )
    ).json()
    project = project_body(
        await create_project(
            client, headers, keywords=["từ khóa cảnh báo <script>"], location=None
        )
    )
    pid = UUID(str(project["id"]))
    keywords = (
        await client.get(f"/api/v1/projects/{pid}/keywords", headers=headers)
    ).json()["items"]
    kid = UUID(keywords[0]["id"])
    settings = app.state.settings.model_copy(
        update={
            "serp_provider": "fake",
            "serp_enabled_providers": "fake",
            "serp_fixed_provider": "fake",
            "serp_provider_priority": "fake",
            "ranking_alert_email_enabled": True,
            "auth_email_provider": "fake",
        }
    )
    router = get_provider_router(settings, app.state.session_factory)
    provider = router.registry.get("fake").provider
    engine = RankCheckExecutionService(app.state.session_factory, router, settings)
    return headers, uid, pid, kid, site, settings, provider, engine


async def observe(engine, provider, pid, kid, uid, position):
    provider.add_result("từ khóa cảnh báo <script>", results(position))
    return await engine.execute_rank_check(pid, kid, uid)


@pytest.mark.integration
@pytest.mark.parametrize(
    "before,after,kind",
    [
        (None, 7, "entered_top10"),
        (6, None, "left_top10"),
        (9, 4, "rank_improved"),
        (2, 6, "rank_declined"),
        (6, 4, None),
        (4, 4, None),
    ],
)
async def test_real_pipeline_and_deduplicated_evaluation(
    auth_client, auth_app, before, after, kind
):
    headers, uid, pid, kid, site, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    first = await observe(engine, provider, pid, kid, uid, before)
    assert await worker.evaluate(first.id)
    assert (await auth_client.get("/api/v1/ranking-alerts", headers=headers)).json()[
        "items"
    ] == []
    second = await observe(engine, provider, pid, kid, uid, after)
    await asyncio.gather(*(worker.evaluate(second.id) for _ in range(4)))
    body = (await auth_client.get("/api/v1/ranking-alerts", headers=headers)).json()
    assert len(body["items"]) == (1 if kind else 0)
    if kind:
        alert = body["items"][0]
        assert alert["alert_type"] == kind
        assert alert["previous_rank"] == before and alert["current_rank"] == after
        assert alert["tracked_site_id"] == site["id"]
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(select(func.count()).select_from(RankingAlertDelivery))
            == 0
        )


@pytest.mark.integration
async def test_partial_failed_and_unknown_baselines(auth_client, auth_app):
    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    await observe(engine, provider, pid, kid, uid, 9)
    provider.add_result("từ khóa cảnh báo <script>", results(None)[:5])
    partial = await engine.execute_rank_check(pid, kid, uid)
    provider.add_error(
        "từ khóa cảnh báo <script>",
        SerpProviderError("SERP_PROVIDER_TIMEOUT", "Timeout"),
    )
    failed = await engine.execute_rank_check(pid, kid, uid)
    current = await observe(engine, provider, pid, kid, uid, 4)
    await worker.drain()
    async with auth_app.state.session_factory() as session:
        assert await session.get(RankingAlertEvaluation, partial.id) is None
        assert await session.get(RankingAlertEvaluation, failed.id) is None
        alert = await session.scalar(select(RankingAlert))
        assert alert.current_observation_id == current.id and alert.previous_rank == 9
        assert alert.alert_type == "rank_improved"


@pytest.mark.integration
async def test_preferences_tenant_pagination_and_read_api(auth_client, auth_app):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    path = f"/api/v1/projects/{pid}/ranking-alert-preferences"
    default = (await auth_client.get(path, headers=headers)).json()
    assert default["movement_threshold"] == 3 and not default["email_enabled"]
    for value in (0, 11, 1.5, True):
        response = await auth_client.put(
            path, headers=headers, json={"movement_threshold": value}
        )
        assert response.status_code == 422
    assert (
        await auth_client.put(path, headers=headers, json={"user_id": str(uid)})
    ).status_code == 422
    assert (
        await auth_client.put(path, headers=headers, json={"movement_threshold": 1})
    ).status_code == 200
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    for position in (9, 7, 4, 8):
        check = await observe(engine, provider, pid, kid, uid, position)
        await worker.evaluate(check.id)
    response = await auth_client.get("/api/v1/ranking-alerts?limit=2", headers=headers)
    body = response.json()
    assert len(body["items"]) == 2 and body["has_more"]
    other = authorization(await register(auth_client, "foreign"))
    aid = body["items"][0]["id"]
    for route, method in [
        (path, "get"),
        (path, "put"),
        (f"/api/v1/ranking-alerts/{aid}/read", "patch"),
        (f"/api/v1/ranking-alerts?project_id={pid}", "get"),
        (f"/api/v1/ranking-alerts/mark-all-read?project_id={pid}", "post"),
    ]:
        kwargs = {"json": {}} if method == "put" else {}
        assert (
            await getattr(auth_client, method)(route, headers=other, **kwargs)
        ).status_code == 404
    assert (await auth_client.get("/api/v1/ranking-alerts", headers=other)).json()[
        "items"
    ] == []
    assert (
        await auth_client.get("/api/v1/ranking-alerts/unread-count", headers=headers)
    ).json()["count"] == 3
    first = (
        await auth_client.patch(f"/api/v1/ranking-alerts/{aid}/read", headers=headers)
    ).json()
    again = (
        await auth_client.patch(f"/api/v1/ranking-alerts/{aid}/read", headers=headers)
    ).json()
    assert first["read_at"] == again["read_at"]
    assert (
        await auth_client.get(
            "/api/v1/ranking-alerts?unread_only=true", headers=headers
        )
    ).json()["items"][0]["id"] != aid
    page2 = (
        await auth_client.get(
            f"/api/v1/ranking-alerts?limit=2&cursor={body['next_cursor']}",
            headers=headers,
        )
    ).json()
    assert len(page2["items"]) == 1 and not page2["has_more"]
    assert (
        await auth_client.post("/api/v1/ranking-alerts/mark-all-read", headers=headers)
    ).status_code == 204
    assert (
        await auth_client.get("/api/v1/ranking-alerts/unread-count", headers=headers)
    ).json()["count"] == 0
    assert (
        await auth_client.get("/api/v1/ranking-alerts?limit=101", headers=headers)
    ).status_code == 422
    assert (
        await auth_client.get("/api/v1/ranking-alerts?cursor=bad", headers=headers)
    ).status_code == 422
    # Existing history deletion protection remains in force.
    assert (
        await auth_client.delete(
            f"/api/v1/projects/{pid}/keywords/{kid}", headers=headers
        )
    ).status_code == 409
    assert (
        await auth_client.delete(f"/api/v1/projects/{pid}", headers=headers)
    ).status_code == 409


@pytest.mark.integration
async def test_environment_change_rebaseline_and_multiple_sites(auth_client, auth_app):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    await observe(engine, provider, pid, kid, uid, 9)
    # An environment edit invalidates the previous complete baseline.
    assert (
        await auth_client.patch(
            f"/api/v1/projects/{pid}",
            headers=headers,
            json={"language_code": "en", "location": "Hanoi"},
        )
    ).status_code == 200
    changed = await observe(engine, provider, pid, kid, uid, 2)
    await worker.evaluate(changed.id)
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0
    second = (
        await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={"name": "Second", "primary_domain": "other1.example"},
        )
    ).json()
    await observe(engine, provider, pid, kid, uid, 2)
    current = await observe(engine, provider, pid, kid, uid, None)
    await worker.evaluate(current.id)
    async with auth_app.state.session_factory() as session:
        alerts = list(await session.scalars(select(RankingAlert)))
        # Second site stayed #1; primary site left Top 10.
        assert len(alerts) == 1 and str(alerts[0].tracked_site_id) != second["id"]
        assert alerts[0].alert_type == "left_top10"


@pytest.mark.integration
async def test_late_arrival_does_not_alert_or_replace_newest(auth_client, auth_app):
    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    first = await observe(engine, provider, pid, kid, uid, 9)
    current = await observe(engine, provider, pid, kid, uid, 4)
    await worker.drain()
    original_start = engine._start

    async def late_start(*args):
        check, request = await original_start(*args)
        async with auth_app.state.session_factory() as session, session.begin():
            stored = await session.get(RankCheck, check.id)
            stored.requested_at = first.requested_at - timedelta(minutes=1)
        return check, request

    engine._start = late_start
    late = await observe(engine, provider, pid, kid, uid, None)
    await worker.drain()
    async with auth_app.state.session_factory() as session:
        evaluation = await session.get(RankingAlertEvaluation, late.id)
        assert evaluation.suppressed
        alerts = list(await session.scalars(select(RankingAlert)))
        assert len(alerts) == 1 and alerts[0].current_observation_id == current.id


@pytest.mark.integration
async def test_email_optin_verified_retry_concurrency_and_escape(auth_client, auth_app):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    async with auth_app.state.session_factory() as session, session.begin():
        user = await session.get(User, uid)
        user.email_verified_at = datetime.now(UTC)
    assert (
        await auth_client.put(
            f"/api/v1/projects/{pid}/ranking-alert-preferences",
            headers=headers,
            json={"email_enabled": True},
        )
    ).status_code == 200
    evaluation = AlertEvaluationService(auth_app.state.session_factory, settings)
    await observe(engine, provider, pid, kid, uid, 9)
    await observe(engine, provider, pid, kid, uid, 3)
    await evaluation.drain()
    async with auth_app.state.session_factory() as session:
        delivery = await session.scalar(select(RankingAlertDelivery))
        did = delivery.id
        recipient = await session.scalar(select(User.email).where(User.id == uid))
    sender = RankingAlertEmailSender(settings)
    worker = AlertEmailWorker(auth_app.state.session_factory, settings, sender)
    original_send = sender.send
    sender.send = AsyncMock(side_effect=AuthEmailError("temporary"))
    await worker.deliver(did)
    async with auth_app.state.session_factory() as session, session.begin():
        delivery = await session.get(RankingAlertDelivery, did)
        assert delivery.status == "pending" and delivery.attempts == 1
        delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    sender.send = original_send
    await asyncio.gather(*(worker.deliver(did) for _ in range(4)))
    assert len(sender.messages) == 1 and sender.messages[0].recipient == recipient
    assert "&lt;script&gt;" in sender.messages[0].html_body
    assert "<script>" not in sender.messages[0].html_body
    async with auth_app.state.session_factory() as session:
        delivery = await session.get(RankingAlertDelivery, did)
        assert delivery.status == "sent" and delivery.attempts == 2
        assert delivery.provider_message_id


@pytest.mark.integration
@pytest.mark.parametrize(
    "reason",
    [
        "unverified",
        "optout",
        "global-off",
        "archived",
        "permanent",
        "throttled",
        "expired-lease",
    ],
)
async def test_email_eligibility_and_recovery(auth_client, auth_app, reason):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    async with auth_app.state.session_factory() as session, session.begin():
        user = await session.get(User, uid)
        user.email_verified_at = datetime.now(UTC)
    await auth_client.put(
        f"/api/v1/projects/{pid}/ranking-alert-preferences",
        headers=headers,
        json={"email_enabled": True},
    )
    await observe(engine, provider, pid, kid, uid, 9)
    await observe(engine, provider, pid, kid, uid, 3)
    await AlertEvaluationService(auth_app.state.session_factory, settings).drain()
    sender = RankingAlertEmailSender(settings)
    async with auth_app.state.session_factory() as session, session.begin():
        delivery = await session.scalar(select(RankingAlertDelivery))
        did = delivery.id
        if reason == "unverified":
            (await session.get(User, uid)).email_verified_at = None
        if reason == "optout":
            await session.execute(
                update(RankingAlertPreference).values(email_enabled=False)
            )
        if reason == "global-off":
            settings = settings.model_copy(
                update={"ranking_alert_email_enabled": False}
            )
        if reason == "archived":
            (await session.get(Project, pid)).status = "archived"
        if reason in ("throttled", "expired-lease"):
            delivery.attempts, delivery.last_attempt_at = 1, datetime.now(UTC)
        if reason == "throttled":
            settings = settings.model_copy(update={"ranking_alert_email_hourly_cap": 1})
        if reason == "expired-lease":
            delivery.status, delivery.lease_token = "sending", uuid4()
            delivery.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    if reason == "permanent":
        sender.send = AsyncMock(side_effect=AuthEmailError("rejected", transient=False))
    await AlertEmailWorker(auth_app.state.session_factory, settings, sender).drain()
    async with auth_app.state.session_factory() as session:
        delivery = await session.get(RankingAlertDelivery, did)
        expected = (
            "sent"
            if reason == "expired-lease"
            else "failed"
            if reason == "permanent"
            else "pending"
            if reason == "throttled"
            else "suppressed"
        )
        assert delivery.status == expected
        assert len(sender.messages) == (1 if reason == "expired-lease" else 0)


@pytest.mark.integration
async def test_evaluation_rollback_and_retry(auth_client, auth_app, monkeypatch):
    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    await observe(engine, provider, pid, kid, uid, 9)
    check = await observe(engine, provider, pid, kid, uid, 3)
    worker = AlertEvaluationService(auth_app.state.session_factory, settings)
    original = worker._create

    async def interrupted(*args):
        await original(*args)
        raise RuntimeError("simulated crash before commit")

    monkeypatch.setattr(worker, "_create", interrupted)
    await worker.drain()
    async with auth_app.state.session_factory() as session, session.begin():
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0
        row = await session.get(RankingAlertEvaluation, check.id)
        assert row.status == "pending" and row.attempts == 1
        row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    monkeypatch.setattr(worker, "_create", original)
    await worker.drain()
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 1


@pytest.mark.integration
async def test_queue_failure_successful_rank_and_recovery(
    auth_client, auth_app, monkeypatch
):
    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    monkeypatch.setattr(
        "app.services.rank_checks.create_task_queue",
        lambda _: (_ for _ in ()).throw(RuntimeError("queue down")),
    )
    await observe(engine, provider, pid, kid, uid, 9)
    check = await observe(engine, provider, pid, kid, uid, 3)
    assert check.status == "succeeded"
    await AlertEvaluationService(auth_app.state.session_factory, settings).drain()
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 1


@pytest.mark.integration
async def test_anonymous_and_verified_gate(auth_client, auth_app):
    assert (await auth_client.get("/api/v1/ranking-alerts")).status_code == 401
    headers, *_ = await setup(auth_client, auth_app)
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"auth_require_verified_email": True}
    )
    assert (
        await auth_client.get("/api/v1/ranking-alerts", headers=headers)
    ).status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize(
    "change",
    [
        {"country_code": "US"},
        {"language_code": "en"},
        {"location": "Hanoi"},
        {"device": "mobile"},
    ],
)
async def test_all_environment_dimensions_rebaseline(auth_client, auth_app, change):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    await observe(engine, provider, pid, kid, uid, 9)
    response = await auth_client.patch(
        f"/api/v1/projects/{pid}", headers=headers, json=change
    )
    assert response.status_code == 200
    current = await observe(engine, provider, pid, kid, uid, 2)
    await AlertEvaluationService(auth_app.state.session_factory, settings).evaluate(
        current.id
    )
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0


@pytest.mark.integration
async def test_partial_first_check_and_provider_warning_never_baseline(
    auth_client, auth_app, monkeypatch
):
    from dataclasses import replace

    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    provider.add_result("từ khóa cảnh báo <script>", results(None)[:5])
    await engine.execute_rank_check(pid, kid, uid)
    original = provider.search

    async def warning(*args, **kwargs):
        return replace(
            await original(*args, **kwargs), raw_metadata={"parsing_warnings": 1}
        )

    monkeypatch.setattr(provider, "search", warning)
    await observe(engine, provider, pid, kid, uid, None)
    monkeypatch.setattr(provider, "search", original)
    current = await observe(engine, provider, pid, kid, uid, 4)
    await AlertEvaluationService(auth_app.state.session_factory, settings).evaluate(
        current.id
    )
    async with auth_app.state.session_factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(RankingAlertEvaluation)
            )
            == 1
        )
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0


@pytest.mark.integration
async def test_alias_edit_rebaseline_and_independent_matching(auth_client, auth_app):
    headers, uid, pid, kid, site, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    await observe(engine, provider, pid, kid, uid, None)
    response = await auth_client.post(
        f"/api/v1/tracked-sites/{site['id']}/domains",
        headers=headers,
        json={"domain": "alias.example"},
    )
    assert response.status_code == 201
    evaluator = AlertEvaluationService(auth_app.state.session_factory, settings)
    provider.add_result("từ khóa cảnh báo <script>", results(7, "alias.example"))
    first = await engine.execute_rank_check(pid, kid, uid)
    await evaluator.evaluate(first.id)
    provider.add_result("từ khóa cảnh báo <script>", results(2, "www.alias.example"))
    second = await engine.execute_rank_check(pid, kid, uid)
    await evaluator.evaluate(second.id)
    async with auth_app.state.session_factory() as session:
        alerts = list(await session.scalars(select(RankingAlert)))
        assert len(alerts) == 1 and alerts[0].alert_type == "rank_improved"
        assert alerts[0].previous_rank == 7 and alerts[0].current_rank == 2


@pytest.mark.integration
async def test_evaluation_time_preferences_disabled_types_and_no_retroactive(
    auth_client, auth_app
):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    await observe(engine, provider, pid, kid, uid, 9)
    current = await observe(engine, provider, pid, kid, uid, 2)
    path = f"/api/v1/projects/{pid}/ranking-alert-preferences"
    await auth_client.put(path, headers=headers, json={"notify_improvement": False})
    evaluator = AlertEvaluationService(auth_app.state.session_factory, settings)
    await evaluator.evaluate(current.id)
    await auth_client.put(path, headers=headers, json={"notify_improvement": True})
    await evaluator.evaluate(current.id)
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0
    await auth_client.put(path, headers=headers, json={"enabled": False})
    await observe(engine, provider, pid, kid, uid, None)
    await evaluator.drain()
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 0


@pytest.mark.integration
async def test_unique_alert_and_delivery_keys_survive_replay(auth_client, auth_app):
    headers, uid, pid, kid, _, settings, provider, engine = await setup(
        auth_client, auth_app
    )
    async with auth_app.state.session_factory() as session, session.begin():
        (await session.get(User, uid)).email_verified_at = datetime.now(UTC)
    await auth_client.put(
        f"/api/v1/projects/{pid}/ranking-alert-preferences",
        headers=headers,
        json={"email_enabled": True},
    )
    await observe(engine, provider, pid, kid, uid, 9)
    check = await observe(engine, provider, pid, kid, uid, 2)
    evaluator = AlertEvaluationService(auth_app.state.session_factory, settings)
    await evaluator.drain()
    # Simulate an operator replay after an ambiguous worker response.
    async with auth_app.state.session_factory() as session, session.begin():
        (await session.get(RankingAlertEvaluation, check.id)).status = "pending"
    await evaluator.evaluate(check.id)
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(RankingAlert)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(RankingAlertDelivery))
            == 1
        )


@pytest.mark.integration
async def test_internal_metrics_are_aggregate_only(auth_client, auth_app):
    from app.services.ranking_alerts import alert_backlog

    _, uid, pid, kid, _, settings, provider, engine = await setup(auth_client, auth_app)
    await observe(engine, provider, pid, kid, uid, 9)
    await observe(engine, provider, pid, kid, uid, 2)
    await AlertEvaluationService(auth_app.state.session_factory, settings).drain()
    metrics = await alert_backlog(auth_app.state.session_factory)
    assert metrics["unread_count"] == 1
    assert metrics["alerts_by_type"] == {"rank_improved": 1}
    assert "keyword" not in str(metrics) and "email" not in str(metrics)
