from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.keyword import Keyword
from app.models.keyword_organization import KeywordTagAssignment
from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def _catalog(
    client: AsyncClient, headers: dict[str, str], project_id: str
) -> tuple[dict, dict, dict]:
    group = await client.post(
        f"/api/v1/projects/{project_id}/keyword-groups",
        headers=headers,
        json={"name": "  Brand  "},
    )
    priority = await client.post(
        f"/api/v1/projects/{project_id}/keyword-tags",
        headers=headers,
        json={"name": "Priority"},
    )
    commercial = await client.post(
        f"/api/v1/projects/{project_id}/keyword-tags",
        headers=headers,
        json={"name": "Commercial"},
    )
    assert group.status_code == priority.status_code == commercial.status_code == 201
    return group.json(), priority.json(), commercial.json()


async def test_catalog_crud_individual_assignment_and_filters(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client, "organization-crud"))
    project = project_body(
        await create_project(auth_client, headers, keywords=["alpha", "beta", "gamma"])
    )
    project_id = str(project["id"])
    group, priority, commercial = await _catalog(auth_client, headers, project_id)
    assert group["name"] == "Brand" and group["active_keyword_count"] == 0
    duplicate = await auth_client.post(
        f"/api/v1/projects/{project_id}/keyword-groups",
        headers=headers,
        json={"name": "brand"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_GROUP_NAME"

    created = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords",
        headers=headers,
        json={
            "keyword": "organized",
            "group_id": group["id"],
            "tag_ids": [priority["id"], commercial["id"]],
        },
    )
    assert created.status_code == 201
    assert created.json()["group"] == {"id": group["id"], "name": "Brand"}
    assert {item["id"] for item in created.json()["tags"]} == {
        priority["id"],
        commercial["id"],
    }
    filtered = await auth_client.get(
        f"/api/v1/projects/{project_id}/keywords",
        headers=headers,
        params={
            "group_id": group["id"],
            "tag_ids": f"{priority['id']},{commercial['id']}",
            "tag_match": "all",
        },
    )
    assert [item["keyword"] for item in filtered.json()["items"]] == ["organized"]
    no_group = await auth_client.get(
        f"/api/v1/projects/{project_id}/keywords",
        headers=headers,
        params={"group_id": "none"},
    )
    assert {item["keyword"] for item in no_group.json()["items"]} == {
        "alpha",
        "beta",
        "gamma",
    }

    updated = await auth_client.patch(
        f"/api/v1/projects/{project_id}/keywords/{created.json()['id']}",
        headers=headers,
        json={"group_id": None, "tag_ids": [priority["id"]]},
    )
    assert updated.status_code == 200
    assert updated.json()["group"] is None
    assert [item["id"] for item in updated.json()["tags"]] == [priority["id"]]

    renamed = await auth_client.patch(
        f"/api/v1/projects/{project_id}/keyword-tags/{priority['id']}",
        headers=headers,
        json={"name": " High   Priority "},
    )
    assert renamed.status_code == 200 and renamed.json()["name"] == "High Priority"


async def test_bulk_operations_are_atomic_and_catalog_deletes_preserve_keywords(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client, "organization-bulk"))
    project = project_body(
        await create_project(auth_client, headers, keywords=["one", "two"])
    )
    foreign_headers = authorization(await register(auth_client, "organization-other"))
    foreign_project = project_body(
        await create_project(
            auth_client, foreign_headers, name="Foreign", keywords=["other"]
        )
    )
    project_id = str(project["id"])
    group, priority, commercial = await _catalog(auth_client, headers, project_id)
    foreign_group, _, _ = await _catalog(
        auth_client, foreign_headers, str(foreign_project["id"])
    )
    items = (
        await auth_client.get(
            f"/api/v1/projects/{project_id}/keywords", headers=headers
        )
    ).json()["items"]
    ids = [item["id"] for item in items]

    assigned = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords/bulk-organize",
        headers=headers,
        json={
            "keyword_ids": ids,
            "operation": "assign_group",
            "group_id": group["id"],
        },
    )
    assert assigned.json()["affected_keyword_count"] == 2
    added = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords/bulk-organize",
        headers=headers,
        json={
            "keyword_ids": ids,
            "operation": "add_tags",
            "tag_ids": [priority["id"], commercial["id"]],
        },
    )
    assert added.json()["assignment_count"] == 4
    invalid = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords/bulk-organize",
        headers=headers,
        json={
            "keyword_ids": ids,
            "operation": "assign_group",
            "group_id": foreign_group["id"],
        },
    )
    assert invalid.status_code == 422
    unchanged = (
        await auth_client.get(
            f"/api/v1/projects/{project_id}/keywords", headers=headers
        )
    ).json()["items"]
    assert {item["group"]["id"] for item in unchanged} == {group["id"]}

    archived = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords/bulk-organize",
        headers=headers,
        json={"keyword_ids": ids, "operation": "archive"},
    )
    assert archived.json()["affected_keyword_count"] == 2
    restored = await auth_client.post(
        f"/api/v1/projects/{project_id}/keywords/bulk-organize",
        headers=headers,
        json={"keyword_ids": ids, "operation": "restore"},
    )
    assert restored.json()["affected_keyword_count"] == 2

    deleted_group = await auth_client.delete(
        f"/api/v1/projects/{project_id}/keyword-groups/{group['id']}",
        headers=headers,
    )
    deleted_tag = await auth_client.delete(
        f"/api/v1/projects/{project_id}/keyword-tags/{priority['id']}",
        headers=headers,
    )
    assert deleted_group.status_code == deleted_tag.status_code == 204
    remaining = (
        await auth_client.get(
            f"/api/v1/projects/{project_id}/keywords", headers=headers
        )
    ).json()["items"]
    assert len(remaining) == 2
    assert all(item["group"] is None for item in remaining)
    assert all(
        {tag["id"] for tag in item["tags"]} == {commercial["id"]} for item in remaining
    )


async def test_database_rejects_cross_project_tag_assignment(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers = authorization(await register(auth_client, "organization-constraint"))
    first = project_body(await create_project(auth_client, headers, keywords=["first"]))
    foreign_headers = authorization(await register(auth_client, "constraint-other"))
    second = project_body(
        await create_project(
            auth_client, foreign_headers, name="Second", keywords=["second"]
        )
    )
    _, foreign_tag, _ = await _catalog(auth_client, foreign_headers, str(second["id"]))
    async with auth_app.state.session_factory() as session, session.begin():
        keyword = await session.scalar(
            select(Keyword).where(Keyword.project_id == UUID(str(first["id"])))
        )
        assert keyword is not None
        with pytest.raises(
            IntegrityError, match="fk_keyword_tag_assignments_tag_project"
        ):
            async with session.begin_nested():
                session.add(
                    KeywordTagAssignment(
                        project_id=keyword.project_id,
                        keyword_id=keyword.id,
                        tag_id=UUID(foreign_tag["id"]),
                    )
                )
                await session.flush()


async def test_bulk_restore_respects_keyword_quota(auth_client: AsyncClient) -> None:
    headers = authorization(await register(auth_client, "organization-quota"))
    project = project_body(
        await create_project(
            auth_client,
            headers,
            keywords=[f"keyword {index}" for index in range(50)],
        )
    )
    endpoint = f"/api/v1/projects/{project['id']}/keywords"
    items = (await auth_client.get(endpoint, headers=headers)).json()["items"]
    archived_id = items[0]["id"]
    assert (
        await auth_client.post(
            f"{endpoint}/bulk-organize",
            headers=headers,
            json={"keyword_ids": [archived_id], "operation": "archive"},
        )
    ).status_code == 200
    assert (
        await auth_client.post(
            endpoint, headers=headers, json={"keyword": "replacement"}
        )
    ).status_code == 201
    restore = await auth_client.post(
        f"{endpoint}/bulk-organize",
        headers=headers,
        json={"keyword_ids": [archived_id], "operation": "restore"},
    )
    assert restore.status_code == 409
    assert restore.json()["error"]["code"] == "KEYWORD_LIMIT_EXCEEDED"
    archived = await auth_client.get(
        endpoint, headers=headers, params={"active": "false"}
    )
    assert [item["id"] for item in archived.json()["items"]] == [archived_id]
