import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import Settings
from app.core.security import hash_refresh_token
from app.main import create_app
from app.models.email_verification import EmailVerificationToken
from app.models.user import User, UserStatus
from app.repositories.refresh_token import RefreshTokenRepository
from app.services.auth_email import AuthEmailError, FakeAuthEmailSender

pytestmark = pytest.mark.integration
SIGNUP = {
    "email": "verification@example.com",
    "password": "a long test password",
    "accept_terms": True,
}


@pytest.fixture
async def verification_app(settings: Settings) -> AsyncIterator[FastAPI]:
    settings = settings.model_copy(
        update={"auth_require_verified_email": True, "auth_email_provider": "fake"}
    )
    schema = f"verification_test_{uuid4().hex}"
    admin = create_async_engine(
        settings.database_url.get_secret_value(), hide_parameters=True
    )
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    app = create_app(settings)
    try:
        async with engine.begin() as connection:

            def migrate(sync_connection):
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")

            await connection.run_sync(migrate)
        async with app.router.lifespan_context(app):
            app.state.session_factory = async_sessionmaker(
                engine, expire_on_commit=False
            )
            yield app
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.fixture
async def verification_client(verification_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=verification_app), base_url="http://test"
    ) as client:
        yield client


def latest_token(app: FastAPI) -> str:
    email = app.state.auth_email_sender.messages[-1]
    return parse_qs(urlsplit(email.url).fragment)["token"][0]


def headers(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def allow_resend(app: FastAPI) -> None:
    async with app.state.session_factory.begin() as session:
        rows = (await session.scalars(select(EmailVerificationToken))).all()
        for row in rows:
            row.created_at = datetime.now(UTC) - timedelta(seconds=61)


async def test_registration_email_commit_gate_and_confirmation(
    verification_client, verification_app, caplog
):
    sender = verification_app.state.auth_email_sender
    original = sender.send

    async def send_after_commit(message):
        async with verification_app.state.session_factory() as session:
            assert await session.scalar(select(User)) is not None
            assert await session.scalar(select(EmailVerificationToken)) is not None
        await original(message)

    sender.send = send_after_commit
    registered = await verification_client.post(
        "/api/v1/auth/register", json=SIGNUP, headers={"Host": "attacker.example"}
    )
    assert registered.status_code == 201
    assert registered.json()["email_verification_required"] is True
    token = latest_token(verification_app)
    assert sender.messages[-1].url.startswith(
        "http://localhost:3000/verify-email#token="
    )
    assert token not in registered.text and token not in caplog.text
    async with verification_app.state.session_factory() as session:
        row = await session.scalar(select(EmailVerificationToken))
        assert row.token_hash == hash_refresh_token(token) and row.token_hash != token
        assert row.delivery_status == "sent"
        assert row.expires_at > datetime.now(UTC)
    me = await verification_client.get("/api/v1/users/me", headers=headers(registered))
    assert me.status_code == 200 and me.json()["email_verified"] is False
    for path in ["/api/v1/projects", "/api/v1/tracked-sites", "/api/v1/billing/me"]:
        blocked = await verification_client.get(path, headers=headers(registered))
        assert blocked.status_code == 403
        assert blocked.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    # Merely opening the URL does not consume a token or create a login session.
    assert (
        await verification_client.get("/api/v1/auth/verify-email")
    ).status_code == 405
    verified = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert verified.status_code == 200
    assert verified.json()["user_id"] == registered.json()["user"]["id"]
    assert "set-cookie" not in verified.headers
    assert verified.headers["cache-control"] == "no-store"
    assert (
        await verification_client.get("/api/v1/projects", headers=headers(registered))
    ).status_code == 200
    restored = await verification_client.post("/api/v1/auth/refresh", json={})
    assert restored.json()["user"]["email_verified"] is True
    reused = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "INVALID_VERIFICATION_TOKEN"


async def test_expiry_invalid_token_and_disabled_account(
    verification_client, verification_app
):
    await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    token = latest_token(verification_app)
    unknown = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": "x" * 64}
    )
    assert unknown.status_code == 400
    async with verification_app.state.session_factory.begin() as session:
        row = await session.scalar(select(EmailVerificationToken))
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    expired = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "VERIFICATION_TOKEN_EXPIRED"
    async with verification_app.state.session_factory.begin() as session:
        user = await session.scalar(select(User))
        user.status = UserStatus.DISABLED
    disabled = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert disabled.status_code == 403


async def test_resend_rotation_cooldown_and_concurrent_requests(
    verification_client, verification_app
):
    registered = await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    old = latest_token(verification_app)
    immediate = await verification_client.post(
        "/api/v1/auth/email-verification/resend", json={}, headers=headers(registered)
    )
    assert immediate.status_code == 429
    assert 0 < immediate.json()["error"]["retry_after_seconds"] <= 60
    await allow_resend(verification_app)
    results = await asyncio.gather(
        *(
            verification_client.post(
                "/api/v1/auth/email-verification/resend",
                json={},
                headers=headers(registered),
            )
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in results) == [200, 429]
    assert len(verification_app.state.auth_email_sender.messages) == 2
    assert (
        await verification_client.post("/api/v1/auth/verify-email", json={"token": old})
    ).status_code == 400
    new = latest_token(verification_app)
    assert new != old
    assert (
        await verification_client.post("/api/v1/auth/verify-email", json={"token": new})
    ).status_code == 200
    no_op = await verification_client.post(
        "/api/v1/auth/email-verification/resend", json={}, headers=headers(registered)
    )
    assert no_op.status_code == 200 and no_op.json()["verified"] is True
    assert len(verification_app.state.auth_email_sender.messages) == 2


async def test_verification_race_is_single_use(verification_client, verification_app):
    await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    token = latest_token(verification_app)
    responses = await asyncio.gather(
        *(
            verification_client.post("/api/v1/auth/verify-email", json={"token": token})
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 400]


async def test_hourly_limit(verification_client, verification_app):
    registered = await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    for _ in range(4):
        await allow_resend(verification_app)
        response = await verification_client.post(
            "/api/v1/auth/email-verification/resend",
            json={},
            headers=headers(registered),
        )
        assert response.status_code == 200
    await allow_resend(verification_app)
    limit = await verification_client.post(
        "/api/v1/auth/email-verification/resend", json={}, headers=headers(registered)
    )
    assert limit.status_code == 429
    assert limit.json()["error"]["retry_after_seconds"] > 3000
    assert len(verification_app.state.auth_email_sender.messages) == 5


async def test_delivery_failure_keeps_account_and_allows_retry(
    verification_client, verification_app, caplog
):
    verification_app.state.auth_email_sender.send = AsyncMock(
        side_effect=AuthEmailError("private smtp credential")
    )
    registered = await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    assert registered.status_code == 201
    state = await verification_client.get(
        "/api/v1/auth/email-verification", headers=headers(registered)
    )
    assert state.json()["delivery_status"] == "failed"
    assert "private smtp credential" not in caplog.text
    await allow_resend(verification_app)
    verification_app.state.auth_email_sender = FakeAuthEmailSender()
    retried = await verification_client.post(
        "/api/v1/auth/email-verification/resend", json={}, headers=headers(registered)
    )
    assert retried.status_code == 200
    verified = await verification_client.post(
        "/api/v1/auth/verify-email", json={"token": latest_token(verification_app)}
    )
    assert verified.status_code == 200


async def test_registration_rollback_sends_no_email(
    verification_client, verification_app, monkeypatch
):
    monkeypatch.setattr(
        RefreshTokenRepository,
        "create",
        AsyncMock(side_effect=RuntimeError("database failure")),
    )
    response = await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    assert response.status_code == 500
    assert verification_app.state.auth_email_sender.messages == []
    async with verification_app.state.session_factory() as session:
        assert (await session.scalars(select(User))).all() == []
        assert (await session.scalars(select(EmailVerificationToken))).all() == []


async def test_resend_requires_login_and_verify_rejects_forms_and_extra_fields(
    verification_client, verification_app
):
    assert (
        await verification_client.post(
            "/api/v1/auth/email-verification/resend", json={}
        )
    ).status_code == 401
    await verification_client.post("/api/v1/auth/register", json=SIGNUP)
    token = latest_token(verification_app)
    for request, status in [
        ({"data": {"token": token}}, 415),
        (
            {
                "json": {"token": token},
                "headers": {"Origin": "https://attacker.example"},
            },
            403,
        ),
        ({"json": {"token": token, "user_id": str(uuid4())}}, 422),
        ({"json": {"token": "short"}}, 422),
    ]:
        response = await verification_client.post(
            "/api/v1/auth/verify-email", **request
        )
        assert response.status_code == status
        assert token not in response.text
    assert (
        await verification_client.post(
            "/api/v1/auth/verify-email", json={"token": token}
        )
    ).status_code == 200
