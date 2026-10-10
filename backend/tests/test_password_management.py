import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from app.core.security import hash_refresh_token, verify_password
from app.models.password_reset import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserStatus
from app.services.auth_email import AuthEmailError, PasswordResetEmail
from tests.test_auth import PASSWORD, SIGNUP, auth_app, auth_client, authorization

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration
NEW_PASSWORD = "a new secure test password"


def reset_token(app):
    email = app.state.auth_email_sender.messages[-1]
    assert isinstance(email, PasswordResetEmail)
    return parse_qs(urlsplit(email.url).fragment)["token"][0]


async def request_reset(client, email=SIGNUP["email"]):
    return await client.post("/api/v1/auth/forgot-password", json={"email": email})


async def reset(client, token, password=NEW_PASSWORD):
    return await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": password}
    )


async def change(client, registered, current=PASSWORD, password=NEW_PASSWORD):
    return await client.post(
        "/api/v1/auth/change-password",
        headers=authorization(registered),
        json={"current_password": current, "new_password": password},
    )


async def age_requests(app):
    async with app.state.session_factory.begin() as session:
        rows = (await session.scalars(select(PasswordResetToken))).all()
        for row in rows:
            row.created_at = datetime.now(UTC) - timedelta(seconds=61)


async def test_reset_email_hash_single_use_password_and_all_sessions(
    auth_client, auth_app, settings, caplog
):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    old_cookie = auth_client.cookies.get(settings.auth_cookie_name)
    second = await auth_client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": PASSWORD}
    )
    sender = auth_app.state.auth_email_sender
    original = sender.send

    async def send_after_commit(message):
        if isinstance(message, PasswordResetEmail):
            async with auth_app.state.session_factory() as session:
                assert await session.scalar(select(PasswordResetToken)) is not None
        await original(message)

    sender.send = send_after_commit
    requested = await request_reset(auth_client, " Person@Example.COM ")
    assert requested.status_code == 200 and requested.json() == {"status": "ok"}
    token = reset_token(auth_app)
    assert sender.messages[-1].url.startswith(
        "http://localhost:3000/reset-password#token="
    )
    async with auth_app.state.session_factory() as session:
        row = await session.scalar(select(PasswordResetToken))
        assert row.token_hash == hash_refresh_token(token) and row.token_hash != token
        assert row.expires_at > datetime.now(UTC)
    assert token not in requested.text and token not in caplog.text
    assert (await auth_client.get("/api/v1/auth/reset-password")).status_code == 405
    changed = await reset(auth_client, token)
    assert changed.status_code == 200
    assert changed.headers["cache-control"] == "no-store"
    assert "Max-Age=0" in changed.headers["set-cookie"]
    assert "access_token" not in changed.text
    assert (await reset(auth_client, token)).status_code == 400
    for issued in [registered, second]:
        assert (
            await auth_client.get("/api/v1/users/me", headers=authorization(issued))
        ).status_code == 401
    assert (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={},
            headers={"Cookie": f"{settings.auth_cookie_name}={old_cookie}"},
        )
    ).status_code == 401
    assert (
        await auth_client.post(
            "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": PASSWORD}
        )
    ).status_code == 401
    logged_in = await auth_client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": NEW_PASSWORD}
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["email_verified"] is False
    async with auth_app.state.session_factory() as session:
        user = await session.scalar(select(User))
        assert user.password_version == 1 and verify_password(
            NEW_PASSWORD, user.password_hash
        )
        row = await session.scalar(select(PasswordResetToken))
        assert row.used_at is not None


async def test_generic_response_rotation_cooldown_and_hourly_limit(
    auth_client, auth_app
):
    unknown = await request_reset(auth_client, "missing@example.com")
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    first = await request_reset(auth_client)
    old = reset_token(auth_app)
    count = len(auth_app.state.auth_email_sender.messages)
    concurrent = await asyncio.gather(
        request_reset(auth_client), request_reset(auth_client)
    )
    for response in [first, *concurrent]:
        assert response.status_code == unknown.status_code == 200
        assert response.json() == unknown.json()
    assert len(auth_app.state.auth_email_sender.messages) == count
    for _ in range(4):
        await age_requests(auth_app)
        assert (await request_reset(auth_client)).status_code == 200
    assert (await reset(auth_client, old)).status_code == 400
    latest = reset_token(auth_app)
    await age_requests(auth_app)
    count = len(auth_app.state.auth_email_sender.messages)
    limited = await request_reset(auth_client)
    assert limited.status_code == 200 and limited.json() == unknown.json()
    assert len(auth_app.state.auth_email_sender.messages) == count
    async with auth_app.state.session_factory.begin() as session:
        user = await session.scalar(select(User))
        user.status = UserStatus.DISABLED
    disabled = await request_reset(auth_client)
    assert disabled.status_code == 200 and disabled.json() == unknown.json()
    assert len(auth_app.state.auth_email_sender.messages) == count
    assert (await reset(auth_client, latest)).status_code == 403


async def test_expired_invalid_and_concurrent_single_use(auth_client, auth_app):
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    await request_reset(auth_client)
    token = reset_token(auth_app)
    assert (await reset(auth_client, "x" * 64)).json()["error"][
        "code"
    ] == "INVALID_PASSWORD_RESET_TOKEN"
    async with auth_app.state.session_factory.begin() as session:
        row = await session.scalar(select(PasswordResetToken))
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await reset(auth_client, token)).status_code == 410
    await age_requests(auth_app)
    await request_reset(auth_client)
    token = reset_token(auth_app)
    results = await asyncio.gather(reset(auth_client, token), reset(auth_client, token))
    assert sorted(r.status_code for r in results) == [200, 400]


async def test_change_checks_current_password_and_keeps_only_new_session(
    auth_client, auth_app, settings
):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    old_cookie = auth_client.cookies.get(settings.auth_cookie_name)
    await request_reset(auth_client)
    token = reset_token(auth_app)
    wrong = await change(auth_client, registered, current="wrong test password")
    assert (
        wrong.status_code == 400
        and wrong.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"
    )
    unchanged = await change(auth_client, registered, password=PASSWORD)
    assert (
        unchanged.status_code == 400
        and unchanged.json()["error"]["code"] == "PASSWORD_UNCHANGED"
    )
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(registered))
    ).status_code == 200
    changed = await change(auth_client, registered)
    assert changed.status_code == 200
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(changed))
    ).status_code == 200
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(registered))
    ).status_code == 401
    assert (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={},
            headers={"Cookie": f"{settings.auth_cookie_name}={old_cookie}"},
        )
    ).status_code == 401
    assert (await reset(auth_client, token)).status_code == 400
    assert (await auth_client.post("/api/v1/auth/refresh", json={})).status_code == 200
    async with auth_app.state.session_factory() as session:
        rows = (await session.scalars(select(RefreshToken))).all()
        assert sum(row.revoked_at is None for row in rows) == 1


async def test_reset_policy_and_mutation_protection(auth_client, auth_app):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    await request_reset(auth_client)
    token = reset_token(auth_app)
    assert (await change(auth_client, registered, password="short")).status_code == 422
    assert (await reset(auth_client, token, "short")).status_code == 422
    assert (await reset(auth_client, token, PASSWORD)).status_code == 400
    for request, status in [
        ({"data": {"token": token, "new_password": NEW_PASSWORD}}, 415),
        (
            {
                "json": {"token": token, "new_password": NEW_PASSWORD},
                "headers": {"Origin": "https://attacker.example"},
            },
            403,
        ),
        (
            {
                "json": {
                    "token": token,
                    "new_password": NEW_PASSWORD,
                    "user_id": registered.json()["user"]["id"],
                }
            },
            422,
        ),
        ({"json": {"token": "short", "new_password": NEW_PASSWORD}}, 422),
    ]:
        response = await auth_client.post("/api/v1/auth/reset-password", **request)
        assert response.status_code == status
        assert token not in response.text and NEW_PASSWORD not in response.text
    unauthenticated = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert unauthenticated.status_code == 401
    assert (await reset(auth_client, token)).status_code == 200


async def test_delivery_failure_is_generic_and_does_not_change_password(
    auth_client, auth_app, caplog
):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    auth_app.state.auth_email_sender.send = AsyncMock(
        side_effect=AuthEmailError("private smtp credential")
    )
    response = await request_reset(auth_client)
    assert response.status_code == 200
    assert "private smtp credential" not in caplog.text
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(registered))
    ).status_code == 200
    assert (
        await auth_client.post(
            "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": PASSWORD}
        )
    ).status_code == 200


async def test_reset_racing_refresh_cannot_leave_a_valid_old_session(
    auth_client, auth_app, settings
):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    raw = auth_client.cookies.get(settings.auth_cookie_name)
    await request_reset(auth_client)
    token = reset_token(auth_app)
    reset_result, refreshed = await asyncio.gather(
        reset(auth_client, token),
        auth_client.post(
            "/api/v1/auth/refresh",
            json={},
            headers={"Cookie": f"{settings.auth_cookie_name}={raw}"},
        ),
    )
    assert reset_result.status_code == 200
    assert refreshed.status_code in {200, 401}
    if refreshed.status_code == 200:
        assert (
            await auth_client.get("/api/v1/users/me", headers=authorization(refreshed))
        ).status_code == 401
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(registered))
    ).status_code == 401
    async with auth_app.state.session_factory() as session:
        assert all(
            row.revoked_at is not None
            for row in (await session.scalars(select(RefreshToken))).all()
        )


async def test_concurrent_changes_accept_current_password_only_once(
    auth_client, auth_app
):
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    results = await asyncio.gather(
        change(auth_client, registered), change(auth_client, registered)
    )
    assert sorted(response.status_code for response in results) == [200, 401]
    async with auth_app.state.session_factory() as session:
        user = await session.scalar(select(User))
        assert user.password_version == 1


async def test_failed_session_issuance_rolls_back_password_and_revocations(
    auth_client, monkeypatch
):
    from app.repositories.refresh_token import RefreshTokenRepository

    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    with monkeypatch.context() as patch:
        patch.setattr(
            RefreshTokenRepository,
            "create",
            AsyncMock(side_effect=RuntimeError("storage unavailable")),
        )
        response = await change(auth_client, registered)
    assert response.status_code == 500
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(registered))
    ).status_code == 200
    assert (
        await auth_client.post(
            "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": PASSWORD}
        )
    ).status_code == 200
