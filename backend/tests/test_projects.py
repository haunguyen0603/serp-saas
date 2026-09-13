from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.models.keyword import Keyword
from app.models.project import Project
from app.repositories.keyword import KeywordRepository
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def test_create_project_atomically_creates_cleaned_keywords(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client))
    created = await create_project(
        auth_client,
        headers,
        keywords=["  First   query ", "", "FIRST QUERY", "Second query"],
    )
    assert created.status_code == 201
    body = created.json()
    project = body["project"]
    UUID(project["id"])
    assert project == {
        **project,
        "name": "Main Website",
        "search_engine": "google",
        "country_code": "VN",
        "language_code": "vi",
        "device": "desktop",
        "location": "Ho Chi Minh City",
        "status": "active",
        "keyword_count": 2,
    }
    assert body["keywords"] == {
        "submitted": 4,
        "normalized_unique": 2,
        "created": 2,
        "skipped_duplicates": 1,
        "skipped_empty": 1,
    }
    assert not {"user_id", "domain", "default_country_code"} & set(project)
    fetched = await auth_client.get(
        f"/api/v1/projects/{project['id']}", headers=headers
    )
    assert fetched.status_code == 200 and fetched.json() == project
    keywords = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords", headers=headers
    )
    assert {item["keyword"] for item in keywords.json()["items"]} == {
        "First query",
        "Second query",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"keywords": []},
        {"keywords": ["", "  "]},
        {"domain": "example.com"},
        {"default_device": "mobile"},
        {"user_id": "00000000-0000-0000-0000-000000000000"},
    ],
)
async def test_create_requires_keywords_and_rejects_old_or_owner_fields(
    auth_client: AsyncClient, change: dict[str, object]
) -> None:
    headers = authorization(await register(auth_client))
    assert (await create_project(auth_client, headers, **change)).status_code == 422


async def test_create_limit_and_transactional_rollback(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers = authorization(await register(auth_client))
    over = await create_project(auth_client, headers, keywords=["x"] * 1001)
    assert over.status_code == 422
    assert over.json()["error"]["code"] == "PROJECT_KEYWORD_LIMIT_EXCEEDED"
    empty = await create_project(auth_client, headers, keywords=["", " "])
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "PROJECT_REQUIRES_KEYWORDS"
    async with auth_app.state.session_factory() as session:
        assert (await session.scalars(select(Project))).all() == []
        assert (await session.scalars(select(Keyword))).all() == []


async def test_unexpected_initial_keyword_failure_rolls_back_project(
    auth_client: AsyncClient,
    auth_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = authorization(await register(auth_client))
    monkeypatch.setattr(
        KeywordRepository,
        "bulk_create_for_project",
        AsyncMock(side_effect=RuntimeError("storage unavailable")),
    )
    response = await create_project(auth_client, headers)
    assert response.status_code == 500
    async with auth_app.state.session_factory() as session:
        assert (await session.scalars(select(Project))).all() == []
        assert (await session.scalars(select(Keyword))).all() == []


async def test_project_list_search_status_cursor_and_counts(
    auth_client: AsyncClient,
    auth_app: FastAPI,
) -> None:
    from tests.business_helpers import grant_plan

    account = await register(auth_client)
    await grant_plan(auth_app, account)
    headers = authorization(account)
    first = await create_project(auth_client, headers, name="Alpha")
    second = await create_project(
        auth_client, headers, name="Beta", keywords=["a", "b"]
    )
    third = await create_project(auth_client, headers, name="Archive")
    ids = [project_body(item)["id"] for item in (first, second, third)]
    await auth_client.patch(
        f"/api/v1/projects/{ids[2]}", headers=headers, json={"status": "archived"}
    )
    page = await auth_client.get("/api/v1/projects?limit=1", headers=headers)
    assert len(page.json()["items"]) == 1 and page.json()["has_more"] is True
    following = await auth_client.get(
        "/api/v1/projects",
        params={"limit": 1, "cursor": page.json()["next_cursor"]},
        headers=headers,
    )
    assert {page.json()["items"][0]["id"], following.json()["items"][0]["id"]} == {
        ids[0],
        ids[1],
    }
    archived = await auth_client.get(
        "/api/v1/projects",
        params={"status": "archived", "search": "Archive"},
        headers=headers,
    )
    assert [item["id"] for item in archived.json()["items"]] == [ids[2]]
    all_projects = await auth_client.get("/api/v1/projects?status=all", headers=headers)
    assert sorted(item["keyword_count"] for item in all_projects.json()["items"]) == [
        1,
        1,
        2,
    ]
    assert (
        await auth_client.get("/api/v1/projects?limit=201", headers=headers)
    ).status_code == 422
    invalid = await auth_client.get("/api/v1/projects?cursor=bad", headers=headers)
    assert (
        invalid.status_code == 422
        and invalid.json()["error"]["code"] == "INVALID_CURSOR"
    )


async def test_project_settings_update_without_mutating_keywords(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client))
    project = project_body(await create_project(auth_client, headers))
    updated = await auth_client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={
            "name": " Updated ",
            "country_code": "th",
            "language_code": "en-us",
            "device": "mobile",
            "location": " Bangkok ",
            "status": "archived",
        },
    )
    assert updated.status_code == 200
    assert updated.json() == {
        **updated.json(),
        "name": "Updated",
        "country_code": "TH",
        "language_code": "en-US",
        "device": "mobile",
        "location": "Bangkok",
        "status": "archived",
        "keyword_count": 1,
    }
    keywords = await auth_client.get(
        f"/api/v1/projects/{project['id']}/keywords?active=all", headers=headers
    )
    assert keywords.json()["items"][0]["keyword"] == "initial keyword"
    assert set(keywords.json()["items"][0]) == {
        "id",
        "keyword",
        "active",
        "created_at",
        "updated_at",
    }


async def test_duplicate_names_allowed_and_delete_cascades(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    from tests.business_helpers import grant_plan

    account = await register(auth_client)
    await grant_plan(auth_app, account)
    headers = authorization(account)
    one = await create_project(auth_client, headers)
    two = await create_project(auth_client, headers)
    assert one.status_code == two.status_code == 201
    assert (
        await auth_client.delete(
            f"/api/v1/projects/{project_body(one)['id']}", headers=headers
        )
    ).status_code == 204
    async with auth_app.state.session_factory() as session:
        assert len((await session.scalars(select(Project))).all()) == 1
        assert len((await session.scalars(select(Keyword))).all()) == 1
