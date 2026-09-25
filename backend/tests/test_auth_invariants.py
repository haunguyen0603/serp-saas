from unittest.mock import AsyncMock

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import inspect, select

from app.core.config import Settings
from app.db.models import Base
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token import RefreshTokenRepository
from tests.test_auth import SIGNUP, auth_app, auth_client

# Reuse the isolated-schema fixtures for these database-level invariants.
__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def test_migration_matches_models(auth_app: FastAPI) -> None:
    async with auth_app.state.session_factory() as session:
        connection = await session.connection()

        def check(sync_connection):
            inspector = inspect(sync_connection)
            assert set(inspector.get_table_names()) == {
                "alembic_version",
                "plans",
                "plan_changes",
                "subscriptions",
                "usage_periods",
                "usage_reservations",
                "usage_events",
                "billing_audit_events",
                "users",
                "refresh_tokens",
                "projects",
                "keywords",
                "tracked_sites",
                "tracked_domains",
                "rank_checks",
                "rank_check_results",
                "rankings",
                "provider_usage",
                "rank_check_provider_attempts",
                "rank_check_batches",
                "rank_check_jobs",
                "project_rank_schedules",
                "keyword_groups",
                "keyword_tags",
                "keyword_tag_assignments",
                "generated_reports",
                "report_schedules",
                "report_delivery_attempts",
            }
            indexes = inspector.get_indexes("refresh_tokens")
            indexed_columns = {tuple(index["column_names"]) for index in indexes}
            assert {("user_id",), ("token_hash",), ("expires_at",)} <= indexed_columns
            assert (
                compare_metadata(
                    MigrationContext.configure(sync_connection), Base.metadata
                )
                == []
            )

        await connection.run_sync(check)


async def test_refresh_hash_is_not_a_bearer_secret(
    auth_client: AsyncClient, auth_app: FastAPI, settings: Settings
) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    async with auth_app.state.session_factory() as session:
        token = await session.scalar(select(RefreshToken))
        hashed = token.token_hash
    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={"Cookie": f"{settings.auth_cookie_name}={hashed}"},
    )
    assert response.status_code == 401


async def test_failed_rotation_preserves_old_session(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    with monkeypatch.context() as patch:
        patch.setattr(
            RefreshTokenRepository,
            "create",
            AsyncMock(side_effect=RuntimeError("private storage failure")),
        )
        failed = await auth_client.post("/api/v1/auth/refresh", json={})
    assert failed.status_code == 500
    assert failed.headers["cache-control"] == "no-store"
    assert (await auth_client.post("/api/v1/auth/refresh", json={})).status_code == 200


async def test_authentication_does_not_depend_on_redis(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    auth_app.state.redis = AsyncMock()
    auth_app.state.redis.ping.side_effect = ConnectionError("unavailable")
    response = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    assert response.status_code == 201
    assert (await auth_client.post("/api/v1/auth/refresh", json={})).status_code == 200
    auth_app.state.redis.ping.assert_not_called()
