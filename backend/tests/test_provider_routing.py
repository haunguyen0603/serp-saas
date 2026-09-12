import asyncio
import logging

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.dependencies.business import get_serp_provider_dependency
from app.models.provider_usage import ProviderUsage
from app.models.rank_check import RankCheck
from app.models.rank_check_provider_attempt import RankCheckProviderAttempt
from app.repositories.provider_usage import ProviderUsageRepository
from app.services.serp import SerpProvider, SerpProviderError
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.registry import (
    ProviderCapabilities,
    ProviderRegistration,
    ProviderRegistry,
)
from app.services.serp.router import ProviderRouter
from app.services.serp.serpapi import SerpApiProvider
from app.services.serp.serper import SerperProvider
from tests.business_helpers import authorization, create_project, project_body, register
from tests.ranking_helpers import execute_engine
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


def registration(
    provider: SerpProvider,
    *,
    configured: bool = True,
    devices: frozenset[str] = frozenset({"desktop", "mobile"}),
    budget: int | None = None,
) -> ProviderRegistration:
    return ProviderRegistration(
        provider=provider,
        configured=configured,
        enabled=True,
        capabilities=ProviderCapabilities(
            supported_search_engines=frozenset({"google"}),
            supported_devices=devices,
        ),
        request_budget=budget,
    )


def use_router(
    app: FastAPI,
    registrations: list[ProviderRegistration],
    *,
    strategy: str = "priority",
    max_fallbacks: int = 1,
) -> ProviderRouter:
    names = tuple(item.provider.name for item in registrations)
    router = ProviderRouter(
        registry=ProviderRegistry(registrations),
        session_factory=app.state.session_factory,
        strategy=strategy,
        priority=names,
        fixed_provider=names[0],
        max_fallbacks=max_fallbacks,
    )
    app.dependency_overrides[get_serp_provider_dependency] = lambda: router
    return router


async def keyword_endpoint(
    client: AsyncClient, device: str = "desktop"
) -> tuple[dict[str, str], str, str]:
    registered = await register(client, "routing")
    headers = authorization(registered)
    project = project_body(
        await create_project(client, headers, keywords=["routing query"], device=device)
    )
    project_id = str(project["id"])
    keywords = (
        await client.get(f"/api/v1/projects/{project_id}/keywords", headers=headers)
    ).json()["items"]
    return headers, project_id, keywords[0]["id"]


@pytest.mark.parametrize(
    "code",
    [
        "SERP_PROVIDER_TIMEOUT",
        "SERP_PROVIDER_UNAVAILABLE",
        "SERP_PROVIDER_RATE_LIMITED",
        "SERP_PROVIDER_QUOTA_EXHAUSTED",
    ],
)
async def test_safe_failure_falls_back_and_persists_attempts(
    auth_client: AsyncClient, auth_app: FastAPI, code: str
) -> None:
    primary = FakeSerpProvider(name="primary")
    primary.add_error("routing query", SerpProviderError(code, "Safe failure"))
    fallback = FakeSerpProvider(name="fallback")
    use_router(auth_app, [registration(primary), registration(fallback)])
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)

    response = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["provider"] == "fallback"
    assert body["provider_request_count"] == 2
    assert [
        (item["provider"], item["status"], item["error_code"])
        for item in body["provider_attempts"]
    ] == [
        ("primary", "failed", code),
        ("fallback", "succeeded", None),
    ]
    async with auth_app.state.session_factory() as session:
        usage = (await session.scalars(select(ProviderUsage))).all()
    assert sum(row.request_count for row in usage) == 2
    assert sum(row.success_count for row in usage) == 1
    assert sum(row.failure_count for row in usage) == 1
    assert sum(row.fallback_count for row in usage) == 1


@pytest.mark.parametrize(
    "code",
    [
        "SERP_PROVIDER_AUTH_ERROR",
        "SERP_PROVIDER_INVALID_REQUEST",
        "SERP_PROVIDER_INVALID_RESPONSE",
    ],
)
async def test_unsafe_failure_does_not_fallback(
    auth_client: AsyncClient, auth_app: FastAPI, code: str
) -> None:
    primary = FakeSerpProvider(name="primary")
    primary.add_error("routing query", SerpProviderError(code, "Safe message"))
    fallback = FakeSerpProvider(name="fallback")
    use_router(auth_app, [registration(primary), registration(fallback)])
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)

    response = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == code
    assert fallback.requests == []
    async with auth_app.state.session_factory() as session:
        check = await session.scalar(select(RankCheck))
        attempts = (await session.scalars(select(RankCheckProviderAttempt))).all()
    assert check is not None and check.provider_request_count == 1
    assert len(attempts) == 1 and attempts[0].error_code == code


async def test_priority_skips_missing_incompatible_and_budget_exhausted_providers(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    missing = FakeSerpProvider(name="missing")
    desktop_only = FakeSerpProvider(name="desktop-only")
    exhausted = FakeSerpProvider(name="exhausted")
    selected = FakeSerpProvider(name="selected")
    use_router(
        auth_app,
        [
            registration(missing, configured=False),
            registration(desktop_only, devices=frozenset({"desktop"})),
            registration(exhausted, budget=1),
            registration(selected),
        ],
    )
    async with auth_app.state.session_factory() as session:
        async with session.begin():
            assert await ProviderUsageRepository(session).reserve_request(
                "exhausted", 1
            )
    headers, project_id, keyword_id = await keyword_endpoint(
        auth_client, device="mobile"
    )

    response = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 201
    assert response.json()["provider"] == "selected"
    assert response.json()["provider_request_count"] == 1
    assert missing.requests == desktop_only.requests == exhausted.requests == []


async def test_fixed_strategy_and_fallback_limit_are_enforced(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    primary = FakeSerpProvider(name="primary")
    primary.add_error(
        "routing query", SerpProviderError("SERP_PROVIDER_TIMEOUT", "Timeout")
    )
    fallback = FakeSerpProvider(name="fallback")
    use_router(
        auth_app,
        [registration(primary), registration(fallback)],
        strategy="fixed",
        max_fallbacks=1,
    )
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)
    response = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 503
    assert fallback.requests == []


async def test_priority_fallback_limit_and_no_provider_error_are_stable(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    primary = FakeSerpProvider(name="primary")
    primary.add_error(
        "routing query", SerpProviderError("SERP_PROVIDER_TIMEOUT", "Timeout")
    )
    fallback = FakeSerpProvider(name="fallback")
    use_router(
        auth_app,
        [registration(primary), registration(fallback)],
        max_fallbacks=0,
    )
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)
    limited = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert limited.status_code == 503
    assert fallback.requests == []

    unavailable = FakeSerpProvider(name="unavailable")
    use_router(auth_app, [registration(unavailable, configured=False)])
    second_project = project_body(
        await create_project(auth_client, headers, keywords=["no provider"])
    )
    second_keywords = (
        await auth_client.get(
            f"/api/v1/projects/{second_project['id']}/keywords", headers=headers
        )
    ).json()["items"]
    missing = await execute_engine(
        auth_app,
        f"/api/v1/projects/{second_project['id']}/keywords/"
        f"{second_keywords[0]['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "SERP_NO_PROVIDER_AVAILABLE"

    use_router(
        auth_app,
        [registration(unavailable, configured=False)],
        strategy="fixed",
    )
    fixed_project = project_body(
        await create_project(auth_client, headers, keywords=["fixed unavailable"])
    )
    fixed_keyword = (
        await auth_client.get(
            f"/api/v1/projects/{fixed_project['id']}/keywords", headers=headers
        )
    ).json()["items"][0]
    fixed = await execute_engine(
        auth_app,
        f"/api/v1/projects/{fixed_project['id']}/keywords/"
        f"{fixed_keyword['id']}/rank-checks",
        headers=headers,
        json={},
    )
    assert fixed.status_code == 503
    assert fixed.json()["error"]["code"] == "SERP_PROVIDER_NOT_CONFIGURED"


async def test_atomic_budget_reservation_prevents_concurrent_overspend(
    auth_app: FastAPI,
) -> None:
    async def reserve() -> bool:
        async with auth_app.state.session_factory() as session:
            async with session.begin():
                return await ProviderUsageRepository(session).reserve_request(
                    "concurrent", 3
                )

    outcomes = await asyncio.gather(*(reserve() for _ in range(12)))
    assert outcomes.count(True) == 3
    async with auth_app.state.session_factory() as session:
        usage = await ProviderUsageRepository(session).current("concurrent")
    assert usage is not None and usage.request_count == 3


async def test_all_budgets_exhausted_uses_no_upstream_requests(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    first = FakeSerpProvider(name="first")
    second = FakeSerpProvider(name="second")
    use_router(
        auth_app,
        [registration(first, budget=1), registration(second, budget=1)],
    )
    async with auth_app.state.session_factory() as session:
        async with session.begin():
            repository = ProviderUsageRepository(session)
            assert await repository.reserve_request("first", 1)
            assert await repository.reserve_request("second", 1)
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)
    response = await execute_engine(
        auth_app,
        f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        headers=headers,
        json={},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERP_NO_PROVIDER_AVAILABLE"
    assert first.requests == second.requests == []


async def test_serper_secret_never_appears_in_logs_api_or_attempts(
    auth_client: AsyncClient,
    auth_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "serper-private-test-key"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401))
    ) as provider_client:
        provider = SerperProvider(
            api_key=secret,
            base_url="https://google.serper.test/search",
            timeout_seconds=1,
            client=provider_client,
        )
        use_router(auth_app, [registration(provider)], strategy="fixed")
        headers, project_id, keyword_id = await keyword_endpoint(auth_client)
        with caplog.at_level(logging.INFO):
            response = await execute_engine(
                auth_app,
                f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
                headers=headers,
                json={},
            )
    assert response.status_code == 502
    async with auth_app.state.session_factory() as session:
        attempt = await session.scalar(select(RankCheckProviderAttempt))
    assert attempt is not None
    assert attempt.error_code == "SERP_PROVIDER_AUTH_ERROR"
    assert secret not in response.text
    assert secret not in caplog.text
    assert secret not in repr(attempt)


async def test_real_adapters_produce_provider_independent_ranking_results(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    headers, project_id, keyword_id = await keyword_endpoint(auth_client)
    site = await auth_client.post(
        "/api/v1/tracked-sites",
        headers=headers,
        json={"name": "Owned", "primary_domain": "owned.example"},
    )
    assert site.status_code == 201

    serpapi_transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "organic_results": [
                    {
                        "position": 2,
                        "title": "Owned",
                        "link": "https://owned.example/page",
                    }
                ]
            },
        )
    )
    serper_transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "organic": [
                    {
                        "position": 2,
                        "title": "Owned",
                        "link": "https://owned.example/page",
                    }
                ]
            },
        )
    )
    async with (
        httpx.AsyncClient(transport=serpapi_transport) as serpapi_client,
        httpx.AsyncClient(transport=serper_transport) as serper_client,
    ):
        adapters = [
            SerpApiProvider(
                api_key="secret",
                base_url="https://serpapi.test/search",
                timeout_seconds=1,
                client=serpapi_client,
            ),
            SerperProvider(
                api_key="secret",
                base_url="https://google.serper.test/search",
                timeout_seconds=1,
                client=serper_client,
            ),
        ]
        outputs = []
        for adapter in adapters:
            use_router(auth_app, [registration(adapter)], strategy="fixed")
            response = await execute_engine(
                auth_app,
                f"/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
                headers=headers,
                json={},
            )
            assert response.status_code == 201
            outputs.append(response.json())
    assert [item["provider"] for item in outputs] == ["serpapi", "serper"]
    assert [item["rankings"][0]["position"] for item in outputs] == [2, 2]
    assert [item["rankings"][0]["matched_domain"] for item in outputs] == [
        "owned.example",
        "owned.example",
    ]
