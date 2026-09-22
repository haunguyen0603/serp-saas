import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.models.keyword import Keyword
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.ranking import Ranking
from app.models.tracked_site import TrackedSite
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def _seed_explorer(
    client: AsyncClient, app: FastAPI
) -> tuple[dict[str, str], UUID, UUID, dict[str, UUID], datetime, datetime]:
    account = await register(client, "explorer-owner")
    headers = authorization(account)
    site_response = await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": "Explorer site", "primary_domain": "explorer.example"},
    )
    assert site_response.status_code == 201
    site = site_response.json()
    names = ["winner", "loser", "stable", "entered", "left", "single", "failed"]
    project = project_body(await create_project(client, headers, keywords=names))
    project_id = UUID(str(project["id"]))
    user_id = UUID(account.json()["user"]["id"])
    site_id = UUID(site["id"])
    domain_id = UUID(site["domains"][0]["id"])
    now = datetime.now(UTC).replace(microsecond=0)
    previous = now - timedelta(days=31)
    current = now - timedelta(minutes=5)
    async with app.state.session_factory() as session, session.begin():
        stored_site = await session.get(TrackedSite, site_id)
        assert stored_site is not None
        stored_site.created_at = previous - timedelta(days=1)
        rows = list(
            (
                await session.scalars(
                    select(Keyword).where(Keyword.project_id == project_id)
                )
            ).all()
        )
        keywords = {row.keyword: row.id for row in rows}
        extra = [
            Keyword(
                project_id=project_id,
                keyword=f"pagination {index:02d}",
                keyword_normalized=f"pagination {index:02d}",
            )
            for index in range(30)
        ]
        session.add_all(extra)
        await session.flush()
        keywords.update({row.keyword: row.id for row in extra})

        def add(
            name: str,
            when: datetime,
            position: int | None,
            status: RankCheckStatus = RankCheckStatus.SUCCEEDED,
        ) -> None:
            check_id = uuid4()
            session.add(
                RankCheck(
                    id=check_id,
                    user_id=user_id,
                    project_id=project_id,
                    keyword_id=keywords[name],
                    provider="fake",
                    status=status,
                    query_snapshot=name,
                    search_engine_snapshot="google",
                    country_code_snapshot="VN",
                    language_code_snapshot="vi",
                    device_snapshot="desktop",
                    location_snapshot=None,
                    result_limit=10,
                    provider_request_count=1,
                    requested_at=when,
                    completed_at=when,
                    created_at=when,
                )
            )
            if position is not None:
                session.add(
                    Ranking(
                        rank_check_id=check_id,
                        tracked_site_id=site_id,
                        tracked_domain_id=domain_id,
                        tracked_site_name_snapshot="Explorer site",
                        matched_domain_snapshot="explorer.example",
                        position=position,
                        result_url="https://explorer.example/page",
                        result_hostname="explorer.example",
                        title=name,
                        created_at=when,
                    )
                )

        for name, old, new in [
            ("winner", 8, 2),
            ("loser", 2, 8),
            ("stable", 5, 5),
            ("entered", None, 4),
            ("left", 4, None),
        ]:
            add(name, previous, old)
            add(name, current, new)
        add("single", current, 3)
        add("failed", current, 1, RankCheckStatus.FAILED)
    return headers, project_id, site_id, keywords, previous, current


async def test_default_filters_sort_and_pagination(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, site_id, _, _, _ = await _seed_explorer(auth_client, auth_app)
    default = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer", headers=headers
    )
    assert default.status_code == 200
    body = default.json()
    assert body["range"] == "30d"
    assert body["effective_depth"] == 10
    assert body["supported_position_buckets"] == [
        "top_3",
        "positions_4_10",
        "not_found_in_depth",
    ]
    assert body["summary"] == {
        "total": 37,
        "improved": 1,
        "declined": 1,
        "unchanged": 1,
        "entered_checked_depth": 1,
        "left_checked_depth": 1,
        "no_previous_data": 1,
        "never_checked": 31,
    }
    assert len(body["items"]) == 37
    by_keyword = {row["keyword"]: row for row in body["items"]}
    assert by_keyword["winner"]["movement"] == {"type": "improved", "change": 6}
    assert by_keyword["entered"]["movement"] == {
        "type": "entered_checked_depth",
        "change": None,
    }
    assert by_keyword["left"]["current"]["position"] is None
    assert by_keyword["left"]["current"]["status"] == "not_found_in_depth"
    assert by_keyword["failed"]["movement"]["type"] == "never_checked"

    improved = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?movement=improved",
        headers=headers,
    )
    assert [row["keyword"] for row in improved.json()["items"]] == ["winner"]
    top_three = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?position_bucket=top_3",
        headers=headers,
    )
    assert {row["keyword"] for row in top_three.json()["items"]} == {
        "single",
        "winner",
    }
    four_to_ten = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer"
        "?position_bucket=positions_4_10",
        headers=headers,
    )
    assert {row["keyword"] for row in four_to_ten.json()["items"]} == {
        "entered",
        "loser",
        "stable",
    }
    not_found = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer"
        "?position_bucket=not_found_in_depth",
        headers=headers,
    )
    assert [row["keyword"] for row in not_found.json()["items"]] == ["left"]
    never_checked = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?status=never_checked",
        headers=headers,
    )
    assert never_checked.json()["summary"]["total"] == 31
    ranked = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?status=ranked",
        headers=headers,
    )
    assert {row["keyword"] for row in ranked.json()["items"]} == {
        "entered",
        "loser",
        "single",
        "stable",
        "winner",
    }
    searched = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?q=%20WIN%20",
        headers=headers,
    )
    assert [row["keyword"] for row in searched.json()["items"]] == ["winner"]
    site_filter = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?tracked_site_id={site_id}",
        headers=headers,
    )
    assert site_filter.json()["summary"]["total"] == 37

    first_page = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?limit=25",
        headers=headers,
    )
    cursor = first_page.json()["page"]["next_cursor"]
    assert len(first_page.json()["items"]) == 25 and cursor
    second_page = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?limit=25&cursor={cursor}",
        headers=headers,
    )
    assert len(second_page.json()["items"]) == 12
    assert second_page.json()["page"]["next_cursor"] is None
    sorted_change = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?sort=change&order=desc",
        headers=headers,
    )
    assert sorted_change.json()["items"][0]["keyword"] == "winner"


async def test_custom_dates_validation_and_tenant_non_disclosure(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, site_id, _, previous, current = await _seed_explorer(
        auth_client, auth_app
    )
    custom = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer"
        f"?compare_from={previous.date()}&compare_to={current.date()}&q=winner",
        headers=headers,
    )
    assert custom.status_code == 200
    assert custom.json()["range"] == "custom"
    assert custom.json()["comparison_basis"] == "custom_dates"
    assert custom.json()["items"][0]["movement"]["type"] == "improved"

    invalid_queries = [
        "movement=unknown",
        "position_bucket=positions_51_100",
        "sort=provider",
        "order=sideways",
        "compare_from=2026-09-02&compare_to=2026-09-01",
        "compare_from=bad&compare_to=2026-09-01",
        "cursor=bad",
    ]
    expected = [
        "INVALID_MOVEMENT_FILTER",
        "INVALID_POSITION_BUCKET",
        "INVALID_SORT_FIELD",
        "INVALID_SORT_ORDER",
        "INVALID_DATE_RANGE",
        "INVALID_DATE_RANGE",
        "INVALID_CURSOR",
    ]
    for query, code in zip(invalid_queries, expected, strict=True):
        response = await auth_client.get(
            f"/api/v1/projects/{project_id}/ranking-explorer?{query}",
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == code

    foreign = authorization(await register(auth_client, "explorer-foreign"))
    foreign_project = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer", headers=foreign
    )
    missing_project = await auth_client.get(
        f"/api/v1/projects/{uuid4()}/ranking-explorer", headers=foreign
    )
    assert foreign_project.status_code == missing_project.status_code == 404
    own_project = project_body(await create_project(auth_client, foreign))
    foreign_site = await auth_client.get(
        f"/api/v1/projects/{own_project['id']}/ranking-explorer"
        f"?tracked_site_id={site_id}",
        headers=foreign,
    )
    assert foreign_site.status_code == 404
    assert foreign_site.json()["error"]["code"] == "TRACKED_SITE_NOT_FOUND"


async def test_explorer_performance_at_one_thousand_keywords_and_two_sites(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    account = await register(auth_client, "explorer-performance")
    headers = authorization(account)
    sites: list[dict] = []
    for index in range(2):
        response = await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={
                "name": f"Performance site {index}",
                "primary_domain": f"performance-{index}.example",
            },
        )
        assert response.status_code == 201
        sites.append(response.json())
    project = project_body(
        await create_project(auth_client, headers, keywords=["keyword 0000"])
    )
    project_id = UUID(str(project["id"]))
    user_id = UUID(account.json()["user"]["id"])
    now = datetime.now(UTC).replace(microsecond=0)
    previous = now - timedelta(days=31)
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
        stored_sites: list[TrackedSite] = []
        for site in sites:
            stored = await session.get(TrackedSite, UUID(site["id"]))
            assert stored is not None
            stored.created_at = previous - timedelta(days=1)
            stored_sites.append(stored)
        await session.flush()
        checks: list[RankCheck] = []
        rankings: list[Ranking] = []
        for index, keyword in enumerate(keywords):
            current_position = (index % 10) + 1
            for when, adjustment in ((previous, 2), (now, 0)):
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
                        location_snapshot=None,
                        result_limit=10,
                        provider_request_count=1,
                        requested_at=when,
                        completed_at=when,
                        created_at=when,
                    )
                )
                for site_index, site in enumerate(sites):
                    position = min(10, current_position + adjustment + site_index)
                    rankings.append(
                        Ranking(
                            rank_check_id=check_id,
                            tracked_site_id=UUID(site["id"]),
                            tracked_domain_id=UUID(site["domains"][0]["id"]),
                            tracked_site_name_snapshot=site["name"],
                            matched_domain_snapshot=site["domains"][0]["domain"],
                            position=position,
                            result_url=f"https://{site['domains'][0]['domain']}/page",
                            result_hostname=site["domains"][0]["domain"],
                            title=keyword.keyword,
                            created_at=when,
                        )
                    )
        session.add_all(checks)
        session.add_all(rankings)

    queries = {
        "default": "",
        "movement": "movement=improved",
        "position": "position_bucket=top_3",
        "search": "q=keyword%200777",
        "change_sort": "sort=change&order=desc",
    }
    timings: dict[str, float] = {}
    first_cursor: str | None = None
    for label, query in queries.items():
        started = perf_counter()
        response = await auth_client.get(
            f"/api/v1/projects/{project_id}/ranking-explorer?{query}",
            headers=headers,
        )
        timings[label] = round((perf_counter() - started) * 1000, 2)
        assert response.status_code == 200
        if label == "default":
            assert response.json()["summary"]["total"] == 2000
            first_cursor = response.json()["page"]["next_cursor"]
    assert first_cursor
    started = perf_counter()
    next_page = await auth_client.get(
        f"/api/v1/projects/{project_id}/ranking-explorer?cursor={first_cursor}",
        headers=headers,
    )
    timings["next_page"] = round((perf_counter() - started) * 1000, 2)
    assert next_page.status_code == 200
    print(json.dumps({"ranking_explorer_performance_ms": timings}))
