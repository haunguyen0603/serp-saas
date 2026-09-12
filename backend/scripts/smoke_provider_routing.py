"""Run a deterministic two-provider fallback smoke with zero real credits."""

import asyncio
import json
import secrets
from uuid import UUID, uuid4

import httpx

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.services.rank_checks import RankCheckExecutionService
from app.services.serp import SerpProviderError
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.registry import (
    ProviderCapabilities,
    ProviderRegistration,
    ProviderRegistry,
)
from app.services.serp.router import ProviderRouter


async def execute(project_id: UUID, keyword_id: UUID, user_id: UUID) -> dict:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    primary = FakeSerpProvider(name="fake-primary")
    primary.add_error(
        "routing smoke",
        SerpProviderError("SERP_PROVIDER_RATE_LIMITED", "Provider rate limited."),
    )
    fallback = FakeSerpProvider(name="fake-fallback")
    capabilities = ProviderCapabilities(
        supported_search_engines=frozenset({"google"}),
        supported_devices=frozenset({"desktop", "mobile"}),
    )
    router = ProviderRouter(
        registry=ProviderRegistry(
            [
                ProviderRegistration(primary, True, True, capabilities),
                ProviderRegistration(fallback, True, True, capabilities),
            ]
        ),
        session_factory=factory,
        strategy="priority",
        priority=("fake-primary", "fake-fallback"),
        fixed_provider=None,
        max_fallbacks=1,
    )
    try:
        return (
            await RankCheckExecutionService(factory, router, settings).run_keyword(
                project_id, keyword_id, user_id
            )
        ).model_dump(mode="json")
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    with httpx.Client(
        base_url=f"http://127.0.0.1:{settings.backend_port}", timeout=15
    ) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"routing-smoke-{uuid4().hex}@example.com",
                "password": secrets.token_urlsafe(24),
                "accept_terms": True,
            },
        )
        assert registered.status_code == 201
        user_id = UUID(registered.json()["user"]["id"])
        headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
        site = client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={"name": "Routing Smoke Site", "primary_domain": "tracked.example"},
        )
        assert site.status_code == 201
        created = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Provider Routing Smoke",
                "search_engine": "google",
                "country_code": "us",
                "language_code": "en",
                "device": "desktop",
                "location": None,
                "keywords": ["routing smoke"],
            },
        )
        assert created.status_code == 201
        project_id = UUID(created.json()["project"]["id"])
        keyword = client.get(
            f"/api/v1/projects/{project_id}/keywords", headers=headers
        ).json()["items"][0]
        result = asyncio.run(execute(project_id, UUID(keyword["id"]), user_id))
        assert result["status"] == "succeeded"
        assert result["provider"] == "fake-fallback"
        assert result["provider_request_count"] == 2
        assert result["result_count"] == 3
        assert len(result["rankings"]) == 1
        assert result["rankings"][0]["matched_domain"] == "tracked.example"
        assert result["rankings"][0]["position"] == 2
        assert [item["status"] for item in result["provider_attempts"]] == [
            "failed",
            "succeeded",
        ]
    print(
        json.dumps(
            {
                "provider_routing_smoke": "passed",
                "strategy": "priority",
                "fallback": "safe rate-limit failure",
                "actual_upstream_requests": 2,
                "real_provider_credits": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
