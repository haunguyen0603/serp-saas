import pytest
from httpx import AsyncClient

from tests.business_helpers import authorization, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def create_site(client: AsyncClient, headers: dict[str, str], **changes: object):
    return await client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={
            "name": "Example Site",
            "primary_domain": "https://Example.com/path?q=1",
            "aliases": ["www.example.com"],
            **changes,
        },
    )


async def test_create_get_list_normalization_and_pagination(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client))
    first = await create_site(auth_client, headers)
    assert first.status_code == 201
    body = first.json()
    assert body["name"] == "Example Site" and body["primary_domain"] == "example.com"
    assert body["domain_alias_count"] == 1
    assert [(item["domain"], item["is_primary"]) for item in body["domains"]] == [
        ("example.com", True),
        ("www.example.com", False),
    ]
    assert not {"user_id", "organization_id"} & set(body)
    fetched = await auth_client.get(
        f"/api/v1/tracked-sites/{body['id']}", headers=headers
    )
    assert fetched.json() == body
    second = await create_site(
        auth_client,
        headers,
        name="Munich",
        primary_domain="HTTPS://münich.example:443/",
        aliases=[],
    )
    assert (
        second.status_code == 201
        and second.json()["primary_domain"] == "xn--mnich-kva.example"
    )
    page = await auth_client.get("/api/v1/tracked-sites?limit=1", headers=headers)
    assert len(page.json()["items"]) == 1 and page.json()["has_more"] is True
    following = await auth_client.get(
        "/api/v1/tracked-sites",
        params={"limit": 1, "cursor": page.json()["next_cursor"]},
        headers=headers,
    )
    assert len(following.json()["items"]) == 1
    search = await auth_client.get(
        "/api/v1/tracked-sites?search=Munich", headers=headers
    )
    assert [item["id"] for item in search.json()["items"]] == [second.json()["id"]]


@pytest.mark.parametrize(
    "domain",
    [
        "",
        "localhost",
        "https://user:pass@example.com",
        "ftp://example.com",
        "bad host.example",
        "https://example.com:bad",
    ],
)
async def test_invalid_domains(auth_client: AsyncClient, domain: str) -> None:
    headers = authorization(await register(auth_client))
    response = await create_site(auth_client, headers, primary_domain=domain)
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"INVALID_DOMAIN", "VALIDATION_ERROR"}


async def test_user_global_uniqueness_and_atomic_create(
    auth_client: AsyncClient,
) -> None:
    headers_a = authorization(await register(auth_client, "a"))
    headers_b = authorization(await register(auth_client, "b"))
    assert (
        await create_site(auth_client, headers_a, aliases=["alias.example"])
    ).status_code == 201
    duplicate = await create_site(
        auth_client, headers_a, name="Duplicate", primary_domain="ALIAS.EXAMPLE"
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error"]["code"] == "DOMAIN_ALREADY_TRACKED"
    )
    listed = await auth_client.get(
        "/api/v1/tracked-sites?status=all", headers=headers_a
    )
    assert len(listed.json()["items"]) == 1
    assert (
        await create_site(auth_client, headers_b, aliases=["alias.example"])
    ).status_code == 201


async def test_301_alias_flow_primary_switch_and_invariants(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client))
    site = (await create_site(auth_client, headers, aliases=[])).json()
    endpoint = f"/api/v1/tracked-sites/{site['id']}/domains"
    added = await auth_client.post(
        endpoint,
        headers=headers,
        json={"domain": "https://new.example/path", "make_primary": False},
    )
    assert added.status_code == 201 and added.json()["domain"] == "new.example"
    old = site["domains"][0]
    assert (
        await auth_client.patch(
            f"{endpoint}/{old['id']}", headers=headers, json={"active": False}
        )
    ).status_code == 409
    assert (
        await auth_client.delete(f"{endpoint}/{old['id']}", headers=headers)
    ).status_code == 409
    promoted = await auth_client.patch(
        f"{endpoint}/{added.json()['id']}", headers=headers, json={"is_primary": True}
    )
    assert (
        promoted.status_code == 200
        and promoted.json()["is_primary"] is True
        and promoted.json()["active"] is True
    )
    deactivated = await auth_client.patch(
        f"{endpoint}/{old['id']}", headers=headers, json={"active": False}
    )
    assert deactivated.status_code == 200 and deactivated.json()["active"] is False
    detail = await auth_client.get(
        f"/api/v1/tracked-sites/{site['id']}", headers=headers
    )
    assert detail.json()["primary_domain"] == "new.example"
    assert (
        await auth_client.patch(
            f"{endpoint}/{added.json()['id']}",
            headers=headers,
            json={"is_primary": False},
        )
    ).status_code == 409


async def test_archive_reactivate_delete_domain_and_site(
    auth_client: AsyncClient,
) -> None:
    headers = authorization(await register(auth_client))
    site = (await create_site(auth_client, headers, aliases=[])).json()
    url = f"/api/v1/tracked-sites/{site['id']}"
    archived = await auth_client.patch(
        url, headers=headers, json={"name": "Renamed", "status": "archived"}
    )
    assert (
        archived.json()["status"] == "archived" and archived.json()["name"] == "Renamed"
    )
    domain = archived.json()["domains"][0]
    assert (
        await auth_client.delete(f"{url}/domains/{domain['id']}", headers=headers)
    ).status_code == 204
    reactivate = await auth_client.patch(
        url, headers=headers, json={"status": "active"}
    )
    assert (
        reactivate.status_code == 409
        and reactivate.json()["error"]["code"] == "PRIMARY_DOMAIN_REQUIRED"
    )
    replacement = await auth_client.post(
        f"{url}/domains",
        headers=headers,
        json={"domain": "replacement.example", "make_primary": True},
    )
    assert replacement.status_code == 201
    assert (
        await auth_client.patch(url, headers=headers, json={"status": "active"})
    ).status_code == 200
    assert (await auth_client.delete(url, headers=headers)).status_code == 204
    assert (await auth_client.get(url, headers=headers)).status_code == 404
