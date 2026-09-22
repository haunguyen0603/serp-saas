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


async def _site(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": "Owned site", "primary_domain": "owned.example"},
    )
    assert response.status_code == 201
    return response.json()


async def test_depth_aware_summary_movers_history_and_tenant_isolation(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    account = await register(auth_client, "analytics-owner")
    headers = authorization(account)
    foreign_headers = authorization(await register(auth_client, "analytics-foreign"))
    site = await _site(auth_client, headers)
    names = ["winner", "loser", "stable", "entered", "left", "single", "failed"]
    project = project_body(
        await create_project(auth_client, headers, keywords=names, device="desktop")
    )
    keyword_rows = (
        await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords?limit=50", headers=headers
        )
    ).json()["items"]
    keywords = {row["keyword"]: UUID(row["id"]) for row in keyword_rows}
    user_id = UUID(account.json()["user"]["id"])
    project_id = UUID(str(project["id"]))
    site_id = UUID(site["id"])
    now = datetime.now(UTC)

    async with auth_app.state.session_factory() as session, session.begin():

        def add_check(
            name: str,
            when: datetime,
            position: int | None,
            *,
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
                        tracked_domain_id=UUID(site["domains"][0]["id"]),
                        tracked_site_name_snapshot="Owned site",
                        matched_domain_snapshot="owned.example",
                        position=position,
                        result_url="https://owned.example/page",
                        result_hostname="owned.example",
                        title=name,
                        created_at=when,
                    )
                )

        previous = now - timedelta(days=31)
        current = now - timedelta(minutes=10)
        stored_site = await session.get(TrackedSite, site_id)
        assert stored_site is not None
        stored_site.created_at = previous - timedelta(days=1)
        for name, old, new in [
            ("winner", 8, 2),
            ("loser", 2, 8),
            ("stable", 5, 5),
            ("entered", None, 4),
            ("left", 4, None),
        ]:
            add_check(name, previous, old)
            add_check(name, current, new)
        add_check("single", current, 3)
        add_check("winner", now - timedelta(hours=2), 6)
        add_check("failed", current, 1, status=RankCheckStatus.FAILED)

    summary_response = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/summary?range=30d&device=desktop",
        headers=headers,
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["distribution"] == {
        "effective_depth": 10,
        "buckets": {
            "top_3": 2,
            "positions_4_10": 3,
            "not_found_in_depth": 1,
        },
    }
    assert {
        key: summary[key]
        for key in (
            "total_keywords",
            "observed_keywords",
            "never_checked",
            "improved",
            "declined",
            "unchanged",
            "newly_ranked",
            "lost_ranking",
            "no_previous_data",
        )
    } == {
        "total_keywords": 7,
        "observed_keywords": 6,
        "never_checked": 1,
        "improved": 1,
        "declined": 1,
        "unchanged": 1,
        "newly_ranked": 1,
        "lost_ranking": 1,
        "no_previous_data": 2,
    }
    assert (
        sum(
            summary[key]
            for key in (
                "improved",
                "declined",
                "unchanged",
                "newly_ranked",
                "lost_ranking",
                "no_previous_data",
            )
        )
        == summary["total_keywords"]
    )

    movers = (
        await auth_client.get(
            f"/api/v1/projects/{project_id}/analytics/movers?range=30d",
            headers=headers,
        )
    ).json()
    assert [(row["keyword"], row["change"]) for row in movers["winners"]] == [
        ("winner", 6)
    ]
    assert [(row["keyword"], row["change"]) for row in movers["losers"]] == [
        ("loser", -6)
    ]

    history = await auth_client.get(
        f"/api/v1/projects/{project_id}/keywords/{keywords['winner']}/ranking-history"
        f"?tracked_site_id={site_id}&range=90d",
        headers=headers,
    )
    assert history.status_code == 200
    points = history.json()["points"]
    assert [point["position"] for point in points] == [8, 2]
    assert all(point["position"] != 101 for point in points)

    invalid_range = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/summary?range=1y", headers=headers
    )
    invalid_device = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/summary?device=mobile",
        headers=headers,
    )
    invalid_limit = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/movers?limit=51", headers=headers
    )
    assert invalid_range.json()["error"]["code"] == "INVALID_ANALYTICS_RANGE"
    assert invalid_device.json()["error"]["code"] == "INVALID_DEVICE_SCOPE"
    assert invalid_limit.status_code == 422

    foreign = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/summary", headers=foreign_headers
    )
    missing = await auth_client.get(
        f"/api/v1/projects/{uuid4()}/analytics/summary", headers=foreign_headers
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


async def test_analytics_queries_are_bounded_for_one_thousand_keywords(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    account = await register(auth_client, "analytics-performance")
    headers = authorization(account)
    site = await _site(auth_client, headers)
    project = project_body(
        await create_project(auth_client, headers, keywords=["keyword 0000"])
    )
    user_id = UUID(account.json()["user"]["id"])
    project_id = UUID(str(project["id"]))
    site_id = UUID(site["id"])
    domain_id = UUID(site["domains"][0]["id"])
    now = datetime.now(UTC)
    async with auth_app.state.session_factory() as session, session.begin():
        first = await session.scalar(
            select(Keyword).where(Keyword.project_id == project_id)
        )
        assert first is not None
        keyword_rows = [first]
        keyword_rows.extend(
            Keyword(
                project_id=project_id,
                keyword=f"keyword {index:04d}",
                keyword_normalized=f"keyword {index:04d}",
            )
            for index in range(1, 1000)
        )
        session.add_all(keyword_rows[1:])
        await session.flush()
        checks: list[RankCheck] = []
        rankings: list[Ranking] = []
        for index, keyword in enumerate(keyword_rows):
            current_position = (index % 10) + 1
            for when, position in (
                (now - timedelta(days=31), min(10, current_position + 2)),
                (now - timedelta(minutes=5), current_position),
            ):
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
                rankings.append(
                    Ranking(
                        rank_check_id=check_id,
                        tracked_site_id=site_id,
                        tracked_domain_id=domain_id,
                        tracked_site_name_snapshot="Owned site",
                        matched_domain_snapshot="owned.example",
                        position=position,
                        result_url="https://owned.example/page",
                        result_hostname="owned.example",
                        title=keyword.keyword,
                        created_at=when,
                    )
                )
        session.add_all(checks)
        session.add_all(rankings)

    started = perf_counter()
    summary = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/summary?range=30d",
        headers=headers,
    )
    summary_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    movers = await auth_client.get(
        f"/api/v1/projects/{project_id}/analytics/movers?range=30d&limit=10",
        headers=headers,
    )
    movers_ms = (perf_counter() - started) * 1000
    assert summary.status_code == movers.status_code == 200
    assert summary.json()["total_keywords"] == 1000
    assert len(movers.json()["winners"]) == 10
    print(
        json.dumps(
            {
                "analytics_performance": "1000_keywords_2_observations",
                "summary_ms": round(summary_ms, 2),
                "movers_ms": round(movers_ms, 2),
            }
        )
    )
