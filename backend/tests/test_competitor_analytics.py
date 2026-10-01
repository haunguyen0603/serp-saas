import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import event, func, select, text

from app.models.keyword import Keyword
from app.models.keyword_organization import (
    KeywordGroup,
    KeywordTag,
    KeywordTagAssignment,
)
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_result import RankCheckResult
from app.models.tracked_site import TrackedSite
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def _site(
    client: AsyncClient, headers: dict[str, str], name: str, domain: str
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": name, "primary_domain": domain},
    )
    assert response.status_code == 201
    return response.json()


async def _seed(
    client: AsyncClient, app: FastAPI
) -> tuple[dict[str, str], UUID, dict[str, dict[str, object]], dict[str, UUID]]:
    account = await register(client, "competitor-owner")
    headers = authorization(account)
    sites = {
        "primary": await _site(client, headers, "My Site", "mine.example"),
        "first": await _site(client, headers, "Competitor A", "competitor.example"),
        "second": await _site(client, headers, "Competitor B", "second.example"),
    }
    project = project_body(
        await create_project(
            client,
            headers,
            keywords=["primary ahead", "competitor ahead", "opportunity", "partial"],
        )
    )
    project_id = UUID(str(project["id"]))
    user_id = UUID(account.json()["user"]["id"])
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=2)
    async with app.state.session_factory() as session, session.begin():
        keywords = {
            row.keyword: row.id
            for row in (
                await session.scalars(
                    select(Keyword).where(Keyword.project_id == project_id)
                )
            ).all()
        }

        def add(name: str, hosts: dict[int, str], *, complete: bool = True) -> None:
            check_id = uuid4()
            session.add(
                RankCheck(
                    id=check_id,
                    user_id=user_id,
                    project_id=project_id,
                    keyword_id=keywords[name],
                    provider="fake",
                    status=RankCheckStatus.SUCCEEDED,
                    query_snapshot=name,
                    search_engine_snapshot="google",
                    country_code_snapshot="VN",
                    language_code_snapshot="vi",
                    device_snapshot="desktop",
                    location_snapshot="Ho Chi Minh City",
                    result_limit=10,
                    provider_request_count=1,
                    requested_at=now,
                    completed_at=now,
                    created_at=now,
                )
            )
            count = 10 if complete else 5

            def result_host(position: int) -> str:
                return hosts.get(position, f"neutral-{position}.example")

            session.add_all(
                RankCheckResult(
                    rank_check_id=check_id,
                    position=position,
                    title=f"Result {position}",
                    url=f"https://{result_host(position)}/page",
                    hostname=result_host(position),
                )
                for position in range(1, count + 1)
            )

        add(
            "primary ahead",
            {2: "mine.example", 5: "competitor.example", 7: "www.mine.example"},
        )
        add("competitor ahead", {3: "www.competitor.example", 8: "mine.example"})
        add("opportunity", {1: "competitor.example", 4: "second.example"})
        add("partial", {2: "mine.example"}, complete=False)
    return headers, project_id, sites, keywords


async def test_selection_is_tenant_safe_and_durable(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, sites, _ = await _seed(auth_client, auth_app)
    other = await register(auth_client, "competitor-other")
    other_site = await _site(
        auth_client, authorization(other), "Other Site", "other.example"
    )
    rejected = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites["primary"]["id"],
            "competitor_tracked_site_ids": [other_site["id"]],
        },
    )
    assert rejected.status_code == 404
    assert rejected.json()["error"]["code"] == "TRACKED_SITE_NOT_FOUND"

    selected = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites["primary"]["id"],
            "competitor_tracked_site_ids": [
                sites["first"]["id"],
                sites["second"]["id"],
            ],
        },
    )
    assert selected.status_code == 200
    assert selected.json()["primary_site"]["name"] == "My Site"
    assert [site["name"] for site in selected.json()["competitor_sites"]] == [
        "Competitor A",
        "Competitor B",
    ]
    assert selected.json()["historical_alias_semantics"] == "current_active_aliases"

    duplicate = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites["primary"]["id"],
            "competitor_tracked_site_ids": [
                sites["first"]["id"],
                sites["first"]["id"],
            ],
        },
    )
    assert duplicate.status_code == 422

    hidden = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=authorization(other),
    )
    assert hidden.status_code == 404
    hidden_analytics = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/overview",
        headers=authorization(other),
    )
    assert hidden_analytics.status_code == 404

    removed = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites["primary"]["id"],
            "competitor_tracked_site_ids": [],
        },
    )
    assert removed.status_code == 200
    async with auth_app.state.session_factory() as session:
        assert await session.get(TrackedSite, UUID(str(sites["first"]["id"])))


async def test_same_check_metrics_opportunities_and_partial_evidence(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, sites, keywords = await _seed(auth_client, auth_app)
    response = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites["primary"]["id"],
            "competitor_tracked_site_ids": [
                sites["first"]["id"],
                sites["second"]["id"],
            ],
        },
    )
    assert response.status_code == 200

    before_checks = 0
    async with auth_app.state.session_factory() as session:
        before_checks = int(await session.scalar(select(func.count(RankCheck.id))) or 0)
    overview = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/overview",
        headers=headers,
    )
    assert overview.status_code == 200
    body = overview.json()
    assert body["qualifying_keywords"] == 4
    assert body["coverage_quality"] == "partial"
    assert body["partial_or_unobserved_keywords"] == 1
    assert body["effective_depth"] == 10
    first = next(
        item
        for item in body["comparisons"]
        if item["opponent_site_id"] == sites["first"]["id"]
    )
    assert first == {
        "opponent_site_id": sites["first"]["id"],
        "opponent_name": "Competitor A",
        "both_numeric_ranked": 2,
        "primary_ahead": 1,
        "tied": 0,
        "competitor_ahead": 1,
        "excluded_unpaired": 2,
        "opportunities": 1,
    }

    table = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/keywords",
        headers=headers,
        params={"opponent_site_id": sites["first"]["id"]},
    )
    assert table.status_code == 200
    rows = {item["keyword"]: item for item in table.json()["items"]}
    assert rows["primary ahead"]["position_gap"] == 3
    assert rows["primary ahead"]["comparison_state"] == "my_site_ahead"
    primary_cell = next(
        site
        for site in rows["primary ahead"]["sites"]
        if site["tracked_site_id"] == sites["primary"]["id"]
    )
    assert primary_cell["position"] == 2  # best of two matching URLs
    assert rows["opportunity"]["opportunity"] is True
    partial_competitor = next(
        site
        for site in rows["partial"]["sites"]
        if site["tracked_site_id"] == sites["first"]["id"]
    )
    assert partial_competitor["status"] == "not_observed"

    opportunities = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/keywords",
        headers=headers,
        params={
            "opponent_site_id": sites["first"]["id"],
            "opportunity": "true",
        },
    )
    assert [item["keyword"] for item in opportunities.json()["items"]] == [
        "opportunity"
    ]
    detail = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/keywords/"
        f"{keywords['primary ahead']}/observations",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["snapshot_complete"] is True
    mine = next(
        site
        for site in detail.json()["sites"]
        if site["tracked_site_id"] == sites["primary"]["id"]
    )
    assert [item["position"] for item in mine["matched_results"]] == [2, 7]

    trends = await auth_client.get(
        f"/api/v1/projects/{project_id}/competitors/trends", headers=headers
    )
    assert trends.status_code == 200
    assert len(trends.json()["points"]) == 1
    assert trends.json()["gaps_are_not_interpolated"] is True
    async with auth_app.state.session_factory() as session:
        assert (
            int(await session.scalar(select(func.count(RankCheck.id))) or 0)
            == before_checks
        )


async def test_competitor_performance_at_one_thousand_keywords_and_four_sites(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    account = await register(auth_client, "competitor-performance")
    headers = authorization(account)
    sites = [
        await _site(
            auth_client,
            headers,
            f"Performance Site {index}",
            f"competitor-performance-{index}.example",
        )
        for index in range(4)
    ]
    project = project_body(
        await create_project(auth_client, headers, keywords=["keyword 0000"])
    )
    project_id = UUID(str(project["id"]))
    user_id = UUID(account.json()["user"]["id"])
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=2)
    previous = now - timedelta(days=1)
    group_ids = [uuid4() for _ in range(10)]
    tag_ids = [uuid4() for _ in range(20)]
    async with auth_app.state.session_factory() as session, session.begin():
        first = await session.scalar(
            select(Keyword).where(Keyword.project_id == project_id)
        )
        assert first is not None
        keywords = [first]
        keywords.extend(
            Keyword(
                project_id=project_id,
                keyword=f"keyword {index:04d}",
                keyword_normalized=f"keyword {index:04d}",
            )
            for index in range(1, 1000)
        )
        session.add_all(keywords[1:])
        session.add_all(
            KeywordGroup(
                id=group_id,
                project_id=project_id,
                name=f"Group {index:02d}",
                normalized_name=f"group {index:02d}",
            )
            for index, group_id in enumerate(group_ids)
        )
        session.add_all(
            KeywordTag(
                id=tag_id,
                project_id=project_id,
                name=f"Tag {index:02d}",
                normalized_name=f"tag {index:02d}",
            )
            for index, tag_id in enumerate(tag_ids)
        )
        await session.flush()
        for index, keyword in enumerate(keywords):
            keyword.keyword_group_id = group_ids[index % len(group_ids)]
            session.add_all(
                KeywordTagAssignment(
                    project_id=project_id,
                    keyword_id=keyword.id,
                    tag_id=tag_id,
                )
                for tag_id in {
                    tag_ids[index % len(tag_ids)],
                    tag_ids[(index + 1) % len(tag_ids)],
                }
            )
        checks: list[RankCheck] = []
        results: list[RankCheckResult] = []
        for keyword_index, keyword in enumerate(keywords):
            for checked_at in (previous, now):
                check_id = uuid4()
                checks.append(
                    RankCheck(
                        id=check_id,
                        user_id=user_id,
                        project_id=project_id,
                        keyword_id=keyword.id,
                        provider="fake",
                        status=RankCheckStatus.SUCCEEDED,
                        query_snapshot=keyword.keyword,
                        search_engine_snapshot="google",
                        country_code_snapshot="VN",
                        language_code_snapshot="vi",
                        device_snapshot="desktop",
                        location_snapshot="Ho Chi Minh City",
                        result_limit=10,
                        provider_request_count=1,
                        requested_at=checked_at,
                        completed_at=checked_at,
                        created_at=checked_at,
                    )
                )
                rotation = keyword_index % 4
                site_by_position = {
                    position + 1: sites[(position + rotation) % 4]["primary_domain"]
                    for position in range(4)
                }

                for position in range(1, 11):
                    hostname = str(
                        site_by_position.get(position, f"neutral-{position}.example")
                    )
                    results.append(
                        RankCheckResult(
                            rank_check_id=check_id,
                            position=position,
                            title=f"{keyword.keyword} result {position}",
                            url=f"https://{hostname}/page",
                            hostname=hostname,
                        )
                    )
        session.add_all(checks)
        session.add_all(results)

    selected = await auth_client.put(
        f"/api/v1/projects/{project_id}/competitor-sites",
        headers=headers,
        json={
            "primary_tracked_site_id": sites[0]["id"],
            "competitor_tracked_site_ids": [site["id"] for site in sites[1:]],
        },
    )
    assert selected.status_code == 200
    engine = auth_app.state.session_factory.kw["bind"]
    query_count = 0

    def count_query(*_args: object) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine.sync_engine, "before_cursor_execute", count_query)
    evidence: dict[str, dict[str, float | int]] = {}

    async def benchmark(label: str, path: str) -> dict[str, object]:
        nonlocal query_count
        query_count = 0
        started = perf_counter()
        response = await auth_client.get(path, headers=headers)
        elapsed = round((perf_counter() - started) * 1000, 2)
        assert response.status_code == 200
        evidence[label] = {"milliseconds": elapsed, "queries": query_count}
        assert query_count <= 8
        return response.json()

    try:
        overview = await benchmark(
            "overview", f"/api/v1/projects/{project_id}/competitors/overview"
        )
        assert overview["qualifying_keywords"] == 1000
        table = await benchmark(
            "keyword_table",
            f"/api/v1/projects/{project_id}/competitors/keywords?limit=25",
        )
        assert table["total"] == 1000 and table["next_cursor"]
        await benchmark(
            "next_page",
            f"/api/v1/projects/{project_id}/competitors/keywords"
            f"?limit=25&cursor={table['next_cursor']}",
        )
        await benchmark(
            "opportunities",
            f"/api/v1/projects/{project_id}/competitors/keywords"
            f"?opponent_site_id={sites[1]['id']}&opportunity=true",
        )
        await benchmark(
            "filtered_table",
            f"/api/v1/projects/{project_id}/competitors/keywords"
            f"?group_id={group_ids[0]}&tag_ids={tag_ids[0]}&tag_match=any",
        )
        await benchmark("trends", f"/api/v1/projects/{project_id}/competitors/trends")
        await benchmark(
            "drill_down",
            f"/api/v1/projects/{project_id}/competitors/keywords/"
            f"{keywords[0].id}/observations",
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count_query)

    async with auth_app.state.session_factory() as session:
        plan = await session.scalar(
            text(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                "SELECT id FROM rank_checks "
                "WHERE project_id = :project_id AND user_id = :user_id "
                "AND status = 'succeeded' AND completed_at >= :start "
                "ORDER BY keyword_id, completed_at DESC, id DESC"
            ),
            {
                "project_id": project_id,
                "user_id": user_id,
                "start": now - timedelta(days=30),
            },
        )
    print(
        json.dumps(
            {
                "competitor_performance": evidence,
                "representative_plan": plan,
            },
            default=str,
            sort_keys=True,
        )
    )
