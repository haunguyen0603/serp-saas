"""Exercise refactored Project/Keyword ownership and CRUD through the API."""

import json
import secrets
from uuid import uuid4

import httpx

from app.core.config import get_settings


def register(client: httpx.Client, label: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"project-smoke-{label}-{uuid4().hex}@example.com",
            "password": secrets.token_urlsafe(24),
            "accept_terms": True,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main() -> None:
    settings = get_settings()
    with (
        httpx.Client(
            base_url=f"http://127.0.0.1:{settings.backend_port}", timeout=15
        ) as user_a,
        httpx.Client(
            base_url=f"http://127.0.0.1:{settings.backend_port}", timeout=15
        ) as user_b,
    ):
        headers_a, headers_b = register(user_a, "a"), register(user_b, "b")
        created = user_a.post(
            "/api/v1/projects",
            headers=headers_a,
            json={
                "name": "Smoke Environment",
                "search_engine": "google",
                "country_code": "vn",
                "language_code": "vi",
                "device": "desktop",
                "location": "Ho Chi Minh City",
                "keywords": ["first", "second", "third"],
            },
        )
        assert created.status_code == 201
        project = created.json()["project"]
        assert (
            created.json()["keywords"]["created"] == 3 and project["keyword_count"] == 3
        )
        assert "domain" not in project and not any(
            key.startswith("default_") for key in project
        )
        project_id = project["id"]
        listed = user_a.get(
            f"/api/v1/projects/{project_id}/keywords", headers=headers_a
        )
        assert listed.status_code == 200 and len(listed.json()["items"]) == 3
        assert all(
            not {"country_code", "language_code", "device", "location"} & set(item)
            for item in listed.json()["items"]
        )
        bulk = user_a.post(
            f"/api/v1/projects/{project_id}/keywords/bulk",
            headers=headers_a,
            json={"keywords": ["third", "fourth", "FOURTH", "fifth"]},
        )
        assert bulk.status_code == 201 and bulk.json()["created"] == 2
        keyword = listed.json()["items"][0]
        updated_project = user_a.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers_a,
            json={"country_code": "TH"},
        )
        assert (
            updated_project.status_code == 200
            and updated_project.json()["country_code"] == "TH"
        )
        assert (
            user_a.get(
                f"/api/v1/projects/{project_id}/keywords/{keyword['id']}",
                headers=headers_a,
            ).json()["keyword"]
            == keyword["keyword"]
        )
        edited = user_a.patch(
            f"/api/v1/projects/{project_id}/keywords/{keyword['id']}",
            headers=headers_a,
            json={"keyword": "updated query", "active": False},
        )
        assert edited.status_code == 200 and edited.json()["active"] is False
        assert (
            user_b.get(f"/api/v1/projects/{project_id}", headers=headers_b).status_code
            == 404
        )
        assert (
            user_b.get(
                f"/api/v1/projects/{project_id}/keywords/{keyword['id']}",
                headers=headers_b,
            ).status_code
            == 404
        )
        assert (
            user_a.delete(
                f"/api/v1/projects/{project_id}/keywords/{keyword['id']}",
                headers=headers_a,
            ).status_code
            == 204
        )
        assert (
            user_a.delete(
                f"/api/v1/projects/{project_id}", headers=headers_a
            ).status_code
            == 204
        )
    print(
        json.dumps(
            {
                "project_keyword_smoke": "passed",
                "checks": [
                    "two_users",
                    "atomic_project_create",
                    "query_only_keywords",
                    "bulk_create",
                    "project_setting_update",
                    "keyword_unchanged",
                    "keyword_edit_pause",
                    "tenant_isolation",
                    "keyword_delete",
                    "project_delete",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
