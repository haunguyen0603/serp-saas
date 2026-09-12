"""Exercise Tracked Site ownership, aliases, and primary switching."""

import json
import secrets
from uuid import uuid4

import httpx

from app.core.config import get_settings


def register(client: httpx.Client, label: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"site-smoke-{label}-{uuid4().hex}@example.com",
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
            "/api/v1/tracked-sites",
            headers=headers_a,
            json={
                "name": "SEO Site A",
                "primary_domain": "new.example",
                "aliases": ["old.example"],
            },
        )
        assert created.status_code == 201
        site_id = created.json()["id"]
        added = user_a.post(
            f"/api/v1/tracked-sites/{site_id}/domains",
            headers=headers_a,
            json={"domain": "newer.example", "make_primary": False},
        )
        assert added.status_code == 201
        promoted = user_a.patch(
            f"/api/v1/tracked-sites/{site_id}/domains/{added.json()['id']}",
            headers=headers_a,
            json={"is_primary": True},
        )
        assert promoted.status_code == 200 and promoted.json()["is_primary"] is True
        detail = user_a.get(f"/api/v1/tracked-sites/{site_id}", headers=headers_a)
        assert detail.json()["primary_domain"] == "newer.example"
        assert {item["domain"] for item in detail.json()["domains"]} == {
            "new.example",
            "old.example",
            "newer.example",
        }
        duplicate = user_a.post(
            "/api/v1/tracked-sites",
            headers=headers_a,
            json={"name": "Duplicate", "primary_domain": "OLD.EXAMPLE"},
        )
        assert duplicate.status_code == 409
        assert (
            user_b.post(
                "/api/v1/tracked-sites",
                headers=headers_b,
                json={"name": "Other User", "primary_domain": "old.example"},
            ).status_code
            == 201
        )
        assert (
            user_b.get(
                f"/api/v1/tracked-sites/{site_id}", headers=headers_b
            ).status_code
            == 404
        )
    print(
        json.dumps(
            {
                "tracked_site_smoke": "passed",
                "checks": [
                    "two_users",
                    "site_create",
                    "initial_alias",
                    "add_alias",
                    "promote_primary",
                    "aliases_retained",
                    "same_user_conflict",
                    "cross_user_domain_allowed",
                    "tenant_isolation",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
