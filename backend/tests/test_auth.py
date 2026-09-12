import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import jwt
import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_password, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserStatus
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth import AuthService

pytestmark = pytest.mark.integration
PASSWORD = "test password with enough length"
SIGNUP = {"email": "person@example.com", "password": PASSWORD, "accept_terms": True}


@pytest.fixture
async def auth_app(app: FastAPI, settings: Settings) -> AsyncIterator[FastAPI]:
    schema = f"auth_test_{uuid4().hex}"
    admin = create_async_engine(settings.database_url.get_secret_value())
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        connect_args={"server_settings": {"search_path": schema}},
    )
    try:
        async with engine.begin() as connection:

            def migrate(sync_connection):
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")

            await connection.run_sync(migrate)
        app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        yield app
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as client:
        yield client


def authorization(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_registration_and_persistence(
    auth_client: AsyncClient, auth_app: FastAPI, settings: Settings
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register", json={**SIGNUP, "email": " Person@Example.COM "}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "person@example.com"
    assert body["user"]["status"] == "active"
    assert body["user"]["email_verified"] is False
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    UUID(body["user"]["id"])
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Secure" not in cookie
    assert "Path=/api/v1/auth" in cookie and "Max-Age=2592000" in cookie
    assert response.headers["cache-control"] == "no-store"
    raw = auth_client.cookies.get(settings.auth_cookie_name)
    async with auth_app.state.session_factory() as session:
        user = await session.scalar(select(User))
        token = await session.scalar(select(RefreshToken))
        assert (
            user.password_hash.startswith("$argon2id$")
            and user.password_hash != PASSWORD
        )
        assert token.token_hash == hash_refresh_token(raw) and token.token_hash != raw
        assert user.terms_accepted_at.tzinfo is not None
        assert user.email_verified_at is None
        assert token.user_id == user.id
        assert token.expires_at > datetime.now(UTC)
        for secret in (
            PASSWORD,
            user.password_hash,
            token.token_hash,
            settings.jwt_secret_key.get_secret_value(),
        ):
            assert secret not in response.text
    me = await auth_client.get("/api/v1/users/me", headers=authorization(response))
    assert me.status_code == 200 and me.json() == body["user"]
    assert me.headers["cache-control"] == "no-store"
    assert set(me.json()) == {
        "id",
        "email",
        "status",
        "email_verified",
        "terms_accepted_at",
        "last_login_at",
        "created_at",
        "updated_at",
    }


@pytest.mark.parametrize(
    "change,code",
    [
        ({"email": "bad"}, "VALIDATION_ERROR"),
        ({"password": "short"}, "PASSWORD_POLICY_VIOLATION"),
        ({"password": "a" * 129}, "PASSWORD_POLICY_VIOLATION"),
        ({"accept_terms": False}, "TERMS_NOT_ACCEPTED"),
        ({"accept_terms": "true"}, "VALIDATION_ERROR"),
        ({"user_id": str(uuid4())}, "VALIDATION_ERROR"),
        ({"status": "active"}, "VALIDATION_ERROR"),
        ({"email_verified": True}, "VALIDATION_ERROR"),
        ({"terms_accepted_at": "2020-01-01"}, "VALIDATION_ERROR"),
        ({"confirm_password": PASSWORD}, "VALIDATION_ERROR"),
    ],
)
async def test_registration_validation(
    auth_client: AsyncClient, change: dict, code: str
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register", json={**SIGNUP, **change}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert PASSWORD not in response.text
    assert response.headers["cache-control"] == "no-store"


async def test_duplicate_and_registration_race(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    responses = await asyncio.gather(
        *(auth_client.post("/api/v1/auth/register", json=SIGNUP) for _ in range(2))
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    failed = next(r for r in responses if r.status_code == 409)
    assert failed.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    async with auth_app.state.session_factory() as session:
        assert len((await session.scalars(select(User))).all()) == 1
        assert len((await session.scalars(select(RefreshToken))).all()) == 1


async def test_login_and_generic_errors(auth_client: AsyncClient) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    unknown = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": PASSWORD},
    )
    wrong = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP["email"], "password": "incorrect password"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert (
        unknown.json()
        == wrong.json()
        == {
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password.",
            }
        }
    )
    good = await auth_client.post(
        "/api/v1/auth/login", json={"email": "PERSON@EXAMPLE.COM", "password": PASSWORD}
    )
    assert good.status_code == 200
    assert good.json()["user"]["last_login_at"] is not None
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(good))
    ).status_code == 200


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing", "AUTHENTICATION_REQUIRED"),
        ("malformed", "INVALID_ACCESS_TOKEN"),
        ("expired", "EXPIRED_ACCESS_TOKEN"),
        ("wrong_type", "INVALID_ACCESS_TOKEN"),
        ("absent_user", "INVALID_ACCESS_TOKEN"),
        ("bad_signature", "INVALID_ACCESS_TOKEN"),
    ],
)
async def test_protected_failures(
    auth_client: AsyncClient, settings: Settings, case: str, code: str
) -> None:
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=1),
        "type": "access",
    }
    if case == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    if case == "wrong_type":
        claims["type"] = "refresh"
    key = (
        settings.jwt_secret_key.get_secret_value()
        if case != "bad_signature"
        else "another-long-test-secret-different"
    )
    token = jwt.encode(claims, key, algorithm="HS256")
    if case == "malformed":
        token = "not-a-token"
    response = await auth_client.get(
        "/api/v1/users/me",
        headers={} if case == "missing" else {"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == code
    assert response.headers["www-authenticate"] == "Bearer"


async def test_refresh_rotation_and_race(
    auth_client: AsyncClient, settings: Settings, auth_app: FastAPI
) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    old = auth_client.cookies.get(settings.auth_cookie_name)
    results = await asyncio.gather(
        *(
            auth_client.post(
                "/api/v1/auth/refresh",
                json={},
                headers={"Cookie": f"{settings.auth_cookie_name}={old}"},
            )
            for _ in range(2)
        )
    )
    assert sorted(r.status_code for r in results) == [200, 401]
    good = next(r for r in results if r.status_code == 200)
    assert old not in good.headers["set-cookie"]
    assert (
        await auth_client.get("/api/v1/users/me", headers=authorization(good))
    ).status_code == 200
    reused = await auth_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={"Cookie": f"{settings.auth_cookie_name}={old}"},
    )
    assert reused.status_code == 401
    async with auth_app.state.session_factory() as session:
        rows = (await session.scalars(select(RefreshToken))).all()
        assert len(rows) == 2
        old_row = next(row for row in rows if row.token_hash == hash_refresh_token(old))
        assert old_row.revoked_at is not None and old_row.last_used_at is not None


@pytest.mark.parametrize("state", ["expired", "revoked"])
async def test_invalid_refresh_state(
    auth_client: AsyncClient, auth_app: FastAPI, state: str
) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    async with auth_app.state.session_factory.begin() as session:
        token = await session.scalar(select(RefreshToken))
        if state == "expired":
            token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        else:
            token.revoked_at = datetime.now(UTC)
    response = await auth_client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_logout(auth_client: AsyncClient, settings: Settings) -> None:
    await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    raw = auth_client.cookies.get(settings.auth_cookie_name)
    response = await auth_client.post("/api/v1/auth/logout", json={})
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert auth_client.cookies.get(settings.auth_cookie_name) is None
    assert (await auth_client.post("/api/v1/auth/logout", json={})).status_code == 200
    assert (await auth_client.post("/api/v1/auth/refresh", json={})).status_code == 401
    replay = await auth_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={"Cookie": f"{settings.auth_cookie_name}={raw}"},
    )
    assert replay.status_code == 401


async def test_disabled_user(auth_client: AsyncClient, auth_app: FastAPI) -> None:
    registered = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    async with auth_app.state.session_factory.begin() as session:
        user = await session.scalar(select(User))
        user.status = UserStatus.DISABLED
    for response in [
        await auth_client.post(
            "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": PASSWORD}
        ),
        await auth_client.post("/api/v1/auth/refresh", json={}),
        await auth_client.get("/api/v1/users/me", headers=authorization(registered)),
    ]:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "DISABLED_USER"


async def test_user_identity_comes_only_from_access_token(
    auth_client: AsyncClient,
) -> None:
    first = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    second = await auth_client.post(
        "/api/v1/auth/register", json={**SIGNUP, "email": "second@example.com"}
    )
    response = await auth_client.get(
        f"/api/v1/users/me?user_id={second.json()['user']['id']}",
        headers={**authorization(first), "X-User-ID": second.json()["user"]["id"]},
    )
    assert response.json()["id"] == first.json()["user"]["id"]


async def test_registration_rolls_back_when_session_storage_fails(
    auth_client: AsyncClient, auth_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        RefreshTokenRepository,
        "create",
        AsyncMock(side_effect=RuntimeError("private database error")),
    )
    response = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
    assert response.status_code == 500
    assert "private" not in response.text and "set-cookie" not in response.headers
    async with auth_app.state.session_factory() as session:
        assert (await session.scalars(select(User))).all() == []


async def test_repositories_and_database_constraints(auth_app: FastAPI) -> None:
    async with auth_app.state.session_factory.begin() as session:
        users = UserRepository(session)
        user = await users.create(
            " RePo@Example.com ", hash_password(PASSWORD), datetime.now(UTC)
        )
        assert user is not None
        assert await users.get_by_email(" REPO@example.COM ") is user
        assert await users.get_by_id(user.id) is user
        tokens = RefreshTokenRepository(session)
        token = await tokens.create(
            user.id,
            hash_refresh_token("test-random-token"),
            datetime.now(UTC) + timedelta(days=1),
        )
        assert await tokens.get_by_hash_for_update(token.token_hash) is token
        await tokens.revoke(token, datetime.now(UTC))
        assert token.revoked_at is not None
        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                session.add(
                    User(
                        email=user.email,
                        password_hash="test",
                        terms_accepted_at=datetime.now(UTC),
                    )
                )
                await session.flush()
        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                session.add(
                    User(
                        email="UPPER@example.com",
                        password_hash="test",
                        terms_accepted_at=datetime.now(UTC),
                    )
                )
                await session.flush()


async def test_service_without_http(auth_app: FastAPI, settings: Settings) -> None:
    async with auth_app.state.session_factory.begin() as session:
        service = AuthService(
            UserRepository(session),
            RefreshTokenRepository(session),
            settings,
            auth_app.state.dummy_password_hash,
        )
        signup = await service.register(RegisterRequest(**SIGNUP))
        login = await service.login(
            LoginRequest(email=SIGNUP["email"], password=PASSWORD)
        )
        assert login.response.user.id == signup.response.user.id
        refreshed = await service.refresh(login.refresh_token)
        assert refreshed.refresh_token != login.refresh_token
        await service.logout(refreshed.refresh_token)
        with pytest.raises(AppError, match="Invalid refresh session"):
            await service.refresh(refreshed.refresh_token)


async def test_csrf_and_credentialed_cors(auth_client: AsyncClient) -> None:
    rejected = await auth_client.post(
        "/api/v1/auth/register",
        json=SIGNUP,
        headers={"Origin": "https://untrusted.example"},
    )
    assert rejected.status_code == 403
    form = await auth_client.post(
        "/api/v1/auth/logout", content="", headers={"Content-Type": "text/plain"}
    )
    assert form.status_code == 415
    preflight = await auth_client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-credentials"] == "true"
    good = await auth_client.post(
        "/api/v1/auth/register",
        json=SIGNUP,
        headers={"Origin": "http://localhost:3000"},
    )
    assert good.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_openapi(auth_client: AsyncClient) -> None:
    schema = (await auth_client.get("/openapi.json")).json()
    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/users/me",
    } <= set(schema["paths"])
    assert schema["paths"]["/api/v1/users/me"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


async def test_auth_logs_exclude_secrets(
    auth_client: AsyncClient, caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    with caplog.at_level(logging.INFO):
        response = await auth_client.post("/api/v1/auth/register", json=SIGNUP)
        await auth_client.get("/api/v1/users/me", headers=authorization(response))
        await auth_client.post("/api/v1/auth/logout", json={})
    for secret in [
        PASSWORD,
        response.json()["access_token"],
        response.cookies.get(settings.auth_cookie_name),
        settings.jwt_secret_key.get_secret_value(),
    ]:
        assert secret not in caplog.text
