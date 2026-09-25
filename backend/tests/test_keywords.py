import asyncio

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.models.keyword import Keyword
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def setup(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = authorization(await register(client))
    return headers, str(project_body(await create_project(client, headers))["id"])


async def test_query_only_create_and_duplicate_normalization(
    auth_client: AsyncClient,
) -> None:
    headers, project_id = await setup(auth_client)
    endpoint = f"/api/v1/projects/{project_id}/keywords"
    created = await auth_client.post(
        endpoint, headers=headers, json={"keyword": "  Café   SEO "}
    )
    assert created.status_code == 201
    assert created.json() == {**created.json(), "keyword": "Café SEO", "active": True}
    assert set(created.json()) == {
        "id",
        "keyword",
        "active",
        "group",
        "tags",
        "created_at",
        "updated_at",
    }
    duplicate = await auth_client.post(
        endpoint, headers=headers, json={"keyword": "CAFE\u0301 SEO"}
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error"]["code"] == "KEYWORD_ALREADY_EXISTS"
    )


@pytest.mark.parametrize(
    "field",
    ["search_engine", "country_code", "language_code", "device", "location", "user_id"],
)
async def test_keyword_rejects_configuration_and_owner_fields(
    auth_client: AsyncClient, field: str
) -> None:
    headers, project_id = await setup(auth_client)
    endpoint = f"/api/v1/projects/{project_id}/keywords"
    assert (
        await auth_client.post(
            endpoint, headers=headers, json={"keyword": "new", field: "x"}
        )
    ).status_code == 422
    assert (
        await auth_client.post(
            f"{endpoint}/bulk", headers=headers, json={"keywords": ["new"], field: "x"}
        )
    ).status_code == 422


async def test_update_pause_resume_collision_delete(auth_client: AsyncClient) -> None:
    headers, project_id = await setup(auth_client)
    endpoint = f"/api/v1/projects/{project_id}/keywords"
    one = await auth_client.post(endpoint, headers=headers, json={"keyword": "one"})
    two = await auth_client.post(endpoint, headers=headers, json={"keyword": "two"})
    url = f"{endpoint}/{one.json()['id']}"
    assert (
        await auth_client.patch(url, headers=headers, json={"active": False})
    ).json()["active"] is False
    edited = await auth_client.patch(
        url, headers=headers, json={"keyword": " edited keyword ", "active": True}
    )
    assert edited.json()["keyword"] == "edited keyword"
    collision = await auth_client.patch(
        f"{endpoint}/{two.json()['id']}",
        headers=headers,
        json={"keyword": "EDITED  KEYWORD"},
    )
    assert collision.status_code == 409
    assert (
        await auth_client.patch(url, headers=headers, json={"device": "mobile"})
    ).status_code == 422
    assert (await auth_client.delete(url, headers=headers)).status_code == 204
    assert (await auth_client.get(url, headers=headers)).status_code == 404


async def test_list_search_state_cursor_bulk_and_limit(
    auth_client: AsyncClient,
) -> None:
    headers, project_id = await setup(auth_client)
    endpoint = f"/api/v1/projects/{project_id}/keywords"
    result = await auth_client.post(
        f"{endpoint}/bulk",
        headers=headers,
        json={
            "keywords": [
                "",
                "initial keyword",
                "alpha one",
                " ALPHA   ONE ",
                "alpha two",
                "paused alpha",
            ]
        },
    )
    assert result.status_code == 201
    assert result.json() == {
        **result.json(),
        "submitted": 6,
        "normalized_unique": 4,
        "created": 3,
        "skipped_duplicates": 2,
        "skipped_empty": 1,
    }
    paused = next(
        item for item in result.json()["items"] if item["keyword"] == "paused alpha"
    )
    await auth_client.patch(
        f"{endpoint}/{paused['id']}", headers=headers, json={"active": False}
    )
    page = await auth_client.get(
        endpoint, params={"search": "alpha", "limit": 1}, headers=headers
    )
    assert len(page.json()["items"]) == 1 and page.json()["has_more"] is True
    following = await auth_client.get(
        endpoint,
        params={"search": "alpha", "limit": 1, "cursor": page.json()["next_cursor"]},
        headers=headers,
    )
    assert len(following.json()["items"]) == 1
    inactive = await auth_client.get(
        endpoint, params={"active": "false"}, headers=headers
    )
    assert [item["keyword"] for item in inactive.json()["items"]] == ["paused alpha"]
    assert (
        await auth_client.post(
            f"{endpoint}/bulk", headers=headers, json={"keywords": ["x"] * 1001}
        )
    ).status_code == 422


async def test_concurrent_duplicate_protection(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id = await setup(auth_client)
    endpoint = f"/api/v1/projects/{project_id}/keywords"
    responses = await asyncio.gather(
        auth_client.post(endpoint, headers=headers, json={"keyword": "Race Keyword"}),
        auth_client.post(endpoint, headers=headers, json={"keyword": "race  keyword"}),
    )
    assert sorted(response.status_code for response in responses) == [201, 409]
    async with auth_app.state.session_factory() as session:
        assert len((await session.scalars(select(Keyword))).all()) == 2
