from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.health import get_redis
from app.db.session import get_db


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.parametrize("path", ["/health/db", "/health/redis"])
async def test_live_dependencies(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_database_unavailable(app: FastAPI, client: AsyncClient) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = ConnectionError("secret database credentials")

    async def failed_db() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = failed_db
    response = await client.get("/health/db")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "secret" not in response.text


async def test_redis_unavailable(app: FastAPI, client: AsyncClient) -> None:
    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("secret redis credentials")
    app.dependency_overrides[get_redis] = lambda: redis
    response = await client.get("/health/redis")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert "secret" not in response.text


async def test_openapi_and_docs(client: AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 200
    schema = (await client.get("/openapi.json")).json()
    assert {"/health", "/health/db", "/health/redis"} <= set(schema["paths"])
    assert "503" in schema["paths"]["/health/db"]["get"]["responses"]


async def test_cors(client: AsyncClient) -> None:
    allowed = await client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = await client.get("/health", headers={"Origin": "https://untrusted.test"})
    assert "access-control-allow-origin" not in denied.headers


async def test_errors_are_consistent(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/test-error")
    async def fail() -> None:
        raise RuntimeError("secret connection string")

    response = await client.get(
        "/test-error", headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        }
    }
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    missing = await client.get("/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
