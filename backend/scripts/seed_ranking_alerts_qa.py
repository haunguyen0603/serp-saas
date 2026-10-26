"""Disposable local QA only: fake complete observations, never real SERP/email."""

import asyncio
import json
import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.keyword import Keyword
from app.models.user import User
from app.services.rank_checks import RankCheckExecutionService
from app.services.ranking_alerts import AlertEvaluationService
from app.services.serp.factory import get_provider_router
from app.services.serp.fake import FakeSerpProvider
from app.services.serp.types import OrganicResult


async def main() -> None:
    settings = get_settings()
    if (
        settings.app_env != "test"
        or settings.serp_provider != "fake"
        or settings.auth_email_provider != "fake"
        or settings.ranking_alert_email_enabled
    ):
        raise SystemExit(
            "QA seed requires test environment, fake providers and outbound alerts off"
        )
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    password = secrets.token_urlsafe(24)
    accounts = {}
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            for name in ("owner", "empty", "unverified"):
                email = f"m7d-{name}-{uuid4().hex}@example.com"
                response = await client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password, "accept_terms": True},
                )
                response.raise_for_status()
                account = response.json()
                uid = UUID(account["user"]["id"])
                if name != "unverified":
                    async with factory() as session, session.begin():
                        user = await session.get(User, uid)
                        assert user
                        user.email_verified_at = datetime.now(UTC)
                accounts[name] = {"email": email, "password": password}
                if name != "owner":
                    continue
                headers = {"Authorization": f"Bearer {account['access_token']}"}
                site_response = await client.post(
                    "/api/v1/tracked-sites",
                    headers=headers,
                    json={
                        "name": "Vietnamese QA site",
                        "primary_domain": "alerts.example",
                    },
                )
                site_response.raise_for_status()
                query = (
                    "theo dõi thứ hạng từ khóa dài dành cho doanh nghiệp Việt Nam " * 3
                )
                response = await client.post(
                    "/api/v1/projects",
                    headers=headers,
                    json={
                        "name": "Ranking Alerts QA",
                        "country_code": "VN",
                        "language_code": "vi",
                        "device": "desktop",
                        "keywords": [query],
                    },
                )
                response.raise_for_status()
                pid = UUID(response.json()["project"]["id"])
                async with factory() as session:
                    kid = await session.scalar(
                        select(Keyword.id).where(Keyword.project_id == pid)
                    )
                assert kid
                router = get_provider_router(settings, factory)
                registration = router.registry.get("fake")
                assert registration and isinstance(
                    registration.provider, FakeSerpProvider
                )
                provider = registration.provider
                checks = RankCheckExecutionService(factory, router, settings)
                evaluator = AlertEvaluationService(factory, settings)
                for position in [None, 7, 2, 8, None, 7] + [2, 8] * 13:
                    rows = [
                        OrganicResult(
                            i,
                            f"Result {i}",
                            "https://"
                            + (
                                "alerts.example"
                                if i == position
                                else f"other{i}.example"
                            )
                            + "/",
                            "alerts.example" if i == position else f"other{i}.example",
                        )
                        for i in range(1, 11)
                    ]
                    provider.add_result(query.strip(), rows)
                    check = await checks.execute_rank_check(pid, kid, uid)
                    await evaluator.evaluate(check.id)
                accounts["project_id"] = str(pid)
            print(json.dumps(accounts))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
