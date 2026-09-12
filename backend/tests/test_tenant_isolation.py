from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.business_helpers import authorization, create_project, project_body, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def test_project_and_keyword_non_disclosure(auth_client: AsyncClient) -> None:
    headers_a = authorization(await register(auth_client, "a"))
    headers_b = authorization(await register(auth_client, "b"))
    project_a = project_body(await create_project(auth_client, headers_a, name="A"))
    project_b = project_body(await create_project(auth_client, headers_b, name="B"))
    keyword = (
        await auth_client.get(
            f"/api/v1/projects/{project_a['id']}/keywords", headers=headers_a
        )
    ).json()["items"][0]
    for method, body in [
        ("get", None),
        ("patch", {"name": "stolen"}),
        ("delete", None),
    ]:
        foreign = await auth_client.request(
            method, f"/api/v1/projects/{project_a['id']}", headers=headers_b, json=body
        )
        missing = await auth_client.request(
            method, f"/api/v1/projects/{uuid4()}", headers=headers_b, json=body
        )
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
    for project, headers in [(project_b, headers_b), (project_a, headers_b)]:
        response = await auth_client.get(
            f"/api/v1/projects/{project['id']}/keywords/{keyword['id']}",
            headers=headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "KEYWORD_NOT_FOUND"


async def test_tracked_site_and_domain_non_disclosure(auth_client: AsyncClient) -> None:
    headers_a = authorization(await register(auth_client, "site-a"))
    headers_b = authorization(await register(auth_client, "site-b"))
    site = (
        await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers_a,
            json={"name": "A", "primary_domain": "a.example"},
        )
    ).json()
    domain = site["domains"][0]
    for method, body in [
        ("get", None),
        ("patch", {"name": "stolen"}),
        ("delete", None),
    ]:
        response = await auth_client.request(
            method, f"/api/v1/tracked-sites/{site['id']}", headers=headers_b, json=body
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRACKED_SITE_NOT_FOUND"
    response = await auth_client.patch(
        f"/api/v1/tracked-sites/{site['id']}/domains/{domain['id']}",
        headers=headers_b,
        json={"active": False},
    )
    assert response.status_code == 404
    wrong_site = (
        await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers_a,
            json={"name": "Other", "primary_domain": "other.example"},
        )
    ).json()
    response = await auth_client.patch(
        f"/api/v1/tracked-sites/{wrong_site['id']}/domains/{domain['id']}",
        headers=headers_a,
        json={"is_primary": True},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRACKED_DOMAIN_NOT_FOUND"


@pytest.mark.parametrize(
    "field", ["user_id", "owner_id", "organization_id", "workspace_id"]
)
async def test_privileged_fields_are_rejected_everywhere(
    auth_client: AsyncClient, field: str
) -> None:
    headers = authorization(await register(auth_client))
    assert (
        await create_project(auth_client, headers, **{field: str(uuid4())})
    ).status_code == 422
    project = project_body(await create_project(auth_client, headers, name="Valid"))
    assert (
        await auth_client.post(
            f"/api/v1/projects/{project['id']}/keywords",
            headers=headers,
            json={"keyword": "secure", field: str(uuid4())},
        )
    ).status_code == 422
    assert (
        await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={
                "name": "Site",
                "primary_domain": "site.example",
                field: str(uuid4()),
            },
        )
    ).status_code == 422


async def test_headers_and_query_cannot_change_owner(auth_client: AsyncClient) -> None:
    registration_a = await register(auth_client, "a")
    registration_b = await register(auth_client, "b")
    headers_a = authorization(registration_a)
    project = project_body(await create_project(auth_client, headers_a))
    response = await auth_client.get(
        f"/api/v1/projects/{project['id']}?user_id={registration_b.json()['user']['id']}",
        headers={**headers_a, "X-User-ID": registration_b.json()["user"]["id"]},
    )
    assert response.status_code == 200
