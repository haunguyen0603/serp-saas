from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASK_QUEUE_PROVIDER", "local")
    monkeypatch.setenv("SERP_PROVIDER", "serpapi")
    monkeypatch.setenv("SERP_ENABLED_PROVIDERS", "")
    monkeypatch.setenv("SERP_FIXED_PROVIDER", "")
    monkeypatch.setenv("SERP_PROVIDER_STRATEGY", "priority")
    monkeypatch.setenv("SERP_PROVIDER_PRIORITY", "serper,serpapi")
    monkeypatch.setenv("SERPAPI_API_KEY", "mock-test-key")
    monkeypatch.setenv("SERPER_API_KEY", "")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_NAME", "serp-saas-test")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    monkeypatch.setenv(
        "JWT_SECRET_KEY", "test-only-placeholder-secret-at-least-32-bytes"
    )
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
