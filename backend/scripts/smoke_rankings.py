"""Run a deterministic, zero-credit ranking pipeline smoke test."""

import asyncio
import json
import secrets
from uuid import UUID, uuid4

import httpx

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.services.rank_checks import RankCheckExecutionService
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.registry import (
    ProviderCapabilities,
    ProviderRegistration,
    ProviderRegistry,
)
from app.services.serp.router import ProviderRouter


def register(client: httpx.Client) -> tuple[dict[str, str], UUID]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"ranking-smoke-{uuid4().hex}@example.com",
            "password": secrets.token_urlsafe(24),
            "accept_terms": True,
        },
    )
    assert response.status_code == 201
    return (
        {"Authorization": f"Bearer {response.json()['access_token']}"},
        UUID(response.json()["user"]["id"]),
    )


async def execute(project_id: UUID, keyword_id: UUID, user_id: UUID) -> dict:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        factory = create_session_factory(engine)
        fake = FakeSerpProvider()
        router = ProviderRouter(
            registry=ProviderRegistry(
                [
                    ProviderRegistration(
                        provider=fake,
                        configured=True,
                        enabled=True,
                        capabilities=ProviderCapabilities(
                            supported_search_engines=frozenset({"google"}),
                            supported_devices=frozenset({"desktop", "mobile"}),
                        ),
                    )
                ]
            ),
            session_factory=factory,
            strategy="fixed",
            priority=("fake",),
            fixed_provider="fake",
            max_fallbacks=0,
        )
        service = RankCheckExecutionService(factory, router, settings)
        return (await service.run_keyword(project_id, keyword_id, user_id)).model_dump(
            mode="json"
        )
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    with httpx.Client(
        base_url=f"http://127.0.0.1:{settings.backend_port}", timeout=15
    ) as client:
        headers, user_id = register(client)
        site = client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={
                "name": "Ranking Smoke Site",
                "primary_domain": "tracked.example",
                "aliases": ["www.secondary.example"],
            },
        )
        assert site.status_code == 201
        project = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Ranking Smoke Project",
                "search_engine": "google",
                "country_code": "vn",
                "language_code": "vi",
                "device": "desktop",
                "location": "Ho Chi Minh City",
                "keywords": ["smoke ranked", "smoke no match"],
            },
        )
        assert project.status_code == 201
        project_id = UUID(project.json()["project"]["id"])
        keywords = client.get(
            f"/api/v1/projects/{project_id}/keywords",
            headers=headers,
            params={"active": "all"},
        ).json()["items"]
        by_query = {item["keyword"]: UUID(item["id"]) for item in keywords}
        matched = asyncio.run(execute(project_id, by_query["smoke ranked"], user_id))
        assert matched["status"] == "succeeded"
        assert matched["provider"] == "fake"
        assert len(matched["provider_attempts"]) == 1
        assert matched["result_count"] == 3
        assert len(matched["rankings"]) == 1
        assert matched["rankings"][0]["position"] == 2
        assert matched["rankings"][0]["matched_domain"] == "tracked.example"

        archived = client.patch(
            f"/api/v1/tracked-sites/{site.json()['id']}",
            headers=headers,
            json={"status": "archived"},
        )
        assert archived.status_code == 200
        no_match = asyncio.run(execute(project_id, by_query["smoke no match"], user_id))
        assert no_match["status"] == "succeeded"
        assert no_match["result_count"] == 3 and no_match["rankings"] == []
        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers,
            json={"country_code": "TH", "device": "mobile"},
        )
        assert updated.status_code == 200
        ranked_keyword_id = by_query["smoke ranked"]
        history = client.get(
            f"/api/v1/projects/{project_id}/keywords/{ranked_keyword_id}/rank-checks",
            headers=headers,
        )
        assert history.status_code == 200
        old = history.json()["items"][0]
        assert old["country_code_snapshot"] == "VN"
        assert old["device_snapshot"] == "desktop"
    print(
        json.dumps(
            {
                "ranking_smoke": "passed",
                "provider": "fake",
                "real_provider_credits": 0,
                "checks": [
                    "registration",
                    "tracked_aliases",
                    "project_keywords",
                    "normalized_top_n",
                    "best_site_position",
                    "no_match_success",
                    "history",
                    "configuration_snapshot",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
