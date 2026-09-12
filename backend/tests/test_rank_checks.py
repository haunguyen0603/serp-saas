import asyncio
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.dependencies.business import get_serp_provider_dependency
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_result import RankCheckResult
from app.models.ranking import Ranking
from app.repositories.ranking import RankingRepository
from app.services.serp import OrganicResult, SerpProviderError
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.registry import (
    ProviderCapabilities,
    ProviderRegistration,
    ProviderRegistry,
)
from app.services.serp.router import ProviderRouter
from tests.business_helpers import (
    authorization,
    create_project,
    project_body,
    register,
)
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


def result(position: int, hostname: str, path: str = "/page") -> OrganicResult:
    return OrganicResult(
        position=position,
        title=f"Result {position}",
        url=f"https://{hostname}{path}",
        hostname=hostname,
    )


def use_fake(app: FastAPI, provider: FakeSerpProvider) -> None:
    router = ProviderRouter(
        registry=ProviderRegistry(
            [
                ProviderRegistration(
                    provider=provider,
                    configured=True,
                    enabled=True,
                    capabilities=ProviderCapabilities(
                        supported_search_engines=frozenset({"google"}),
                        supported_devices=frozenset({"desktop", "mobile"}),
                    ),
                )
            ]
        ),
        session_factory=app.state.session_factory,
        strategy="fixed",
        priority=(provider.name,),
        fixed_provider=provider.name,
        max_fallbacks=0,
    )
    app.dependency_overrides[get_serp_provider_dependency] = lambda: router


async def create_site(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
    primary: str,
    aliases: list[str] | None = None,
) -> dict:
    response = await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": name, "primary_domain": primary, "aliases": aliases or []},
    )
    assert response.status_code == 201
    return response.json()


async def test_full_fake_pipeline_snapshots_history_and_tenant_isolation(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    user_a = await register(auth_client, "ranking-a")
    headers_a = authorization(user_a)
    user_b = await register(auth_client, "ranking-b")
    headers_b = authorization(user_b)
    site_a = await create_site(
        auth_client, headers_a, "Site A", "new-a.example", ["old-a.example"]
    )
    site_b = await create_site(auth_client, headers_a, "Site B", "site-b.example")
    await create_site(auth_client, headers_b, "Foreign", "competitor.example")
    project = project_body(
        await create_project(
            auth_client,
            headers_a,
            keywords=["rank tracker"],
            country_code="vn",
            language_code="vi",
            device="desktop",
            location="Ho Chi Minh City",
        )
    )
    keywords = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords", headers=headers_a
        )
    ).json()["items"]
    keyword = keywords[0]
    provider = FakeSerpProvider()
    provider.add_result(
        "rank tracker",
        [
            result(1, "competitor.example"),
            result(2, "old-a.example", "/first"),
            result(3, "other.example"),
            result(5, "site-b.example", "/owned"),
            result(7, "new-a.example", "/second"),
        ],
    )
    use_fake(auth_app, provider)

    checked = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks",
        headers=headers_a,
        json={},
    )
    assert checked.status_code == 201
    body = checked.json()
    assert body["status"] == "succeeded"
    assert body["result_count"] == 5
    assert [
        (item["tracked_site_name"], item["position"]) for item in body["rankings"]
    ] == [
        ("Site A", 2),
        ("Site B", 5),
    ]
    assert body["rankings"][0]["matched_domain"] == "old-a.example"
    assert body["rankings"][0]["result_url"].endswith("/first")
    assert "Foreign" not in checked.text
    check_id = body["id"]

    latest = await auth_client.get(
        f"/api/v1/projects/{project['id']}/rankings/latest", headers=headers_a
    )
    assert latest.status_code == 200
    assert latest.json()["items"][0]["latest_check"]["id"] == check_id
    history = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks",
        headers=headers_a,
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["rankings"][0]["position"] == 2
    foreign = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks/{check_id}",
        headers=headers_b,
    )
    missing = await auth_client.get(
        f"/api/v1/projects/{uuid4()}/keywords/{uuid4()}/rank-checks/{uuid4()}",
        headers=headers_b,
    )
    assert foreign.status_code == missing.status_code == 404

    await auth_client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers_a,
        json={"country_code": "TH", "device": "mobile"},
    )
    await auth_client.patch(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}",
        headers=headers_a,
        json={"keyword": "renamed rank tracker"},
    )
    old_alias = next(
        domain for domain in site_a["domains"] if domain["domain"] == "old-a.example"
    )
    await auth_client.patch(
        f"/api/v1/tracked-sites/{site_a['id']}/domains/{old_alias['id']}",
        headers=headers_a,
        json={"active": False},
    )
    await auth_client.patch(
        f"/api/v1/tracked-sites/{site_a['id']}",
        headers=headers_a,
        json={"name": "Renamed Site A"},
    )
    detail = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks/{check_id}",
        headers=headers_a,
    )
    snapshot = detail.json()
    assert snapshot["query_snapshot"] == "rank tracker"
    assert snapshot["country_code_snapshot"] == "VN"
    assert snapshot["device_snapshot"] == "desktop"
    assert snapshot["location_snapshot"] == "Ho Chi Minh City"
    assert snapshot["rankings"][0]["tracked_site_name"] == "Site A"
    assert snapshot["rankings"][0]["matched_domain"] == "old-a.example"

    for path in [
        f"/api/v1/projects/{project['id']}",
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}",
        f"/api/v1/tracked-sites/{site_a['id']}",
        f"/api/v1/tracked-sites/{site_b['id']}",
    ]:
        response = await auth_client.delete(path, headers=headers_a)
        expected = 409 if path != f"/api/v1/tracked-sites/{site_b['id']}" else 409
        assert response.status_code == expected
        assert response.json()["error"]["code"] == "HISTORY_EXISTS"

    delete_alias = await auth_client.delete(
        f"/api/v1/tracked-sites/{site_a['id']}/domains/{old_alias['id']}",
        headers=headers_a,
    )
    assert delete_alias.status_code == 409
    assert delete_alias.json()["error"]["code"] == "HISTORY_EXISTS"


async def test_zero_match_empty_results_and_provider_failure_are_distinct(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    registered = await register(auth_client, "ranking-states")
    headers = authorization(registered)
    project = project_body(
        await create_project(
            auth_client,
            headers,
            keywords=["no match", "empty", "timeout"],
        )
    )
    keyword_rows = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords",
            headers=headers,
            params={"active": "all"},
        )
    ).json()["items"]
    by_name = {row["keyword"]: row for row in keyword_rows}
    provider = FakeSerpProvider()
    provider.add_result("no match", [result(1, "competitor.example")])
    provider.add_result("empty", [])
    provider.add_error(
        "timeout",
        SerpProviderError(
            "SERP_PROVIDER_TIMEOUT", "The SERP provider timed out.", request_count=1
        ),
    )
    use_fake(auth_app, provider)
    for name, count in [("no match", 1), ("empty", 0)]:
        response = await auth_client.post(
            f"/api/v1/projects/{project['id']}/keywords/{by_name[name]['id']}/rank-checks",
            headers=headers,
            json={},
        )
        assert response.status_code == 201
        assert response.json()["status"] == "succeeded"
        assert response.json()["result_count"] == count
        assert response.json()["rankings"] == []
    failed = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{by_name['timeout']['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert failed.status_code == 503
    assert failed.json()["error"] == {
        "code": "SERP_PROVIDER_TIMEOUT",
        "message": "The SERP provider timed out.",
    }
    history = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords/{by_name['timeout']['id']}/rank-checks",
        headers=headers,
    )
    assert history.json()["items"][0]["status"] == "failed"
    assert history.json()["items"][0]["provider_request_count"] == 1
    aggregate = await auth_client.post(
        f"/api/v1/projects/{project['id']}/rank-checks",
        headers=headers,
        json={
            "keyword_ids": [
                by_name["no match"]["id"],
                by_name["timeout"]["id"],
            ]
        },
    )
    assert aggregate.status_code == 201
    assert aggregate.json()["submitted_keywords"] == 2
    assert aggregate.json()["succeeded"] == 1
    assert aggregate.json()["failed"] == 1
    no_match_history = (
        f"/api/v1/projects/{project['id']}/keywords/"
        f"{by_name['no match']['id']}/rank-checks"
    )
    first_page = await auth_client.get(
        no_match_history,
        headers=headers,
        params={"limit": 1},
    )
    assert first_page.json()["has_more"] is True
    second_page = await auth_client.get(
        no_match_history,
        headers=headers,
        params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["id"] != first_page.json()["items"][0]["id"]


async def test_project_check_subset_cap_status_and_input_security(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    registered = await register(auth_client, "ranking-project")
    headers = authorization(registered)
    project = project_body(
        await create_project(
            auth_client,
            headers,
            keywords=[f"keyword {index}" for index in range(26)],
        )
    )
    keywords = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords",
            headers=headers,
            params={"limit": 50, "active": "all"},
        )
    ).json()["items"]
    use_fake(auth_app, FakeSerpProvider())
    over_cap = await auth_client.post(
        f"/api/v1/projects/{project['id']}/rank-checks", headers=headers, json={}
    )
    assert over_cap.status_code == 400
    assert over_cap.json()["error"]["code"] == "RANK_CHECK_LIMIT_EXCEEDED"
    selected = await auth_client.post(
        f"/api/v1/projects/{project['id']}/rank-checks",
        headers=headers,
        json={"keyword_ids": [keywords[0]["id"], keywords[1]["id"]]},
    )
    assert selected.status_code == 201
    assert selected.json()["submitted_keywords"] == 2
    assert selected.json()["succeeded"] == 2
    for injected_body in [
        {"user_id": str(uuid4())},
        {"provider": "serper"},
        {"provider": "serpapi"},
        {"serper_request_budget": 999999},
    ]:
        injected = await auth_client.post(
            f"/api/v1/projects/{project['id']}/keywords/"
            f"{keywords[2]['id']}/rank-checks",
            headers=headers,
            json=injected_body,
        )
        assert injected.status_code == 422
    await auth_client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"status": "archived"},
    )
    archived = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{keywords[2]['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert archived.status_code == 400
    assert archived.json()["error"]["code"] == "PROJECT_NOT_ACTIVE"
    await auth_client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"status": "active"},
    )
    await auth_client.patch(
        f"/api/v1/projects/{project['id']}/keywords/{keywords[2]['id']}",
        headers=headers,
        json={"active": False},
    )
    paused = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{keywords[2]['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert paused.status_code == 400
    assert paused.json()["error"]["code"] == "KEYWORD_NOT_ACTIVE"


async def test_inactive_alias_and_archived_site_do_not_match(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    registered = await register(auth_client, "ranking-active")
    headers = authorization(registered)
    inactive_site = await create_site(
        auth_client,
        headers,
        "Aliases",
        "primary.example",
        ["inactive.example"],
    )
    archived_site = await create_site(
        auth_client, headers, "Archived", "archived.example"
    )
    alias = next(
        domain for domain in inactive_site["domains"] if not domain["is_primary"]
    )
    await auth_client.patch(
        f"/api/v1/tracked-sites/{inactive_site['id']}/domains/{alias['id']}",
        headers=headers,
        json={"active": False},
    )
    await auth_client.patch(
        f"/api/v1/tracked-sites/{archived_site['id']}",
        headers=headers,
        json={"status": "archived"},
    )
    project = project_body(await create_project(auth_client, headers))
    keyword = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords", headers=headers
        )
    ).json()["items"][0]
    provider = FakeSerpProvider()
    provider.add_result(
        keyword["keyword"],
        [
            result(1, "inactive.example"),
            result(2, "archived.example"),
            result(3, "www.primary.example"),
        ],
    )
    use_fake(auth_app, provider)
    response = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 201
    assert [
        (value["matched_domain"], value["position"])
        for value in response.json()["rankings"]
    ] == [("primary.example", 3)]


async def test_concurrent_checks_execute_provider_once(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    registered = await register(auth_client, "ranking-race")
    headers = authorization(registered)
    project = project_body(await create_project(auth_client, headers))
    keyword = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords", headers=headers
        )
    ).json()["items"][0]
    provider = FakeSerpProvider(delay_seconds=0.2)
    use_fake(auth_app, provider)

    async def run() -> object:
        return await auth_client.post(
            f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks",
            headers=headers,
            json={},
        )

    responses = await asyncio.gather(run(), run())
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert len(provider.requests) == 1
    async with auth_app.state.session_factory() as session:
        checks = list((await session.scalars(select(RankCheck))).all())
        assert len(checks) == 1 and checks[0].status is RankCheckStatus.SUCCEEDED
        assert len((await session.scalars(select(RankCheckResult))).all()) == 3
        assert len((await session.scalars(select(Ranking))).all()) == 0


async def test_success_persistence_rolls_back_atomically_and_marks_failed(
    auth_client: AsyncClient,
    auth_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = await register(auth_client, "ranking-atomic")
    headers = authorization(registered)
    await create_site(auth_client, headers, "Owned", "tracked.example")
    project = project_body(await create_project(auth_client, headers))
    keyword = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords", headers=headers
        )
    ).json()["items"][0]
    use_fake(auth_app, FakeSerpProvider())

    async def fail_rankings(*args: object, **kwargs: object) -> list[Ranking]:
        raise RuntimeError("database detail that must not escape")

    monkeypatch.setattr(RankingRepository, "create_many", fail_rankings)
    response = await auth_client.post(
        f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "RANK_CHECK_PERSISTENCE_ERROR"
    assert "database detail" not in response.text
    async with auth_app.state.session_factory() as session:
        check = await session.scalar(select(RankCheck))
        assert check is not None and check.status is RankCheckStatus.FAILED
        assert check.error_code == "RANK_CHECK_PERSISTENCE_ERROR"
        assert (await session.scalars(select(RankCheckResult))).all() == []
        assert (await session.scalars(select(Ranking))).all() == []
