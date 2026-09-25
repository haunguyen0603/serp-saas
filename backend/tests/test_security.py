from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hashing() -> None:
    password = "a long test password"
    hashed = hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert password not in hashed
    assert verify_password(password, hashed)
    assert not verify_password("different password", hashed)
    assert not verify_password(password, "invalid hash")
    assert hash_password(password) != hashed


def test_access_token(settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, settings)
    assert decode_access_token(token, settings) == user_id
    payload = jwt.decode(
        token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"]
    )
    assert set(payload) == {"sub", "type", "iat", "exp"}
    assert payload["exp"] - payload["iat"] == 900


@pytest.mark.parametrize(
    "case",
    [
        "expired",
        "wrong_type",
        "missing_exp",
        "bad_sub",
        "bad_signature",
        "wrong_algorithm",
        "future_iat",
        "malformed",
    ],
)
def test_invalid_tokens(settings: Settings, case: str) -> None:
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=1),
    }
    key = settings.jwt_secret_key.get_secret_value()
    algorithm = "HS256"
    if case == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    if case == "wrong_type":
        claims["type"] = "refresh"
    if case == "missing_exp":
        del claims["exp"]
    if case == "bad_sub":
        claims["sub"] = "not-a-uuid"
    if case == "bad_signature":
        key = "different-test-signing-secret-32-bytes"
    if case == "wrong_algorithm":
        algorithm = "HS384"
        key = key * 2
    if case == "future_iat":
        claims["iat"] = now + timedelta(hours=1)
    token = (
        "malformed"
        if case == "malformed"
        else jwt.encode(claims, key, algorithm=algorithm)
    )
    with pytest.raises(AppError) as error:
        decode_access_token(token, settings)
    assert error.value.code == (
        "EXPIRED_ACCESS_TOKEN" if case == "expired" else "INVALID_ACCESS_TOKEN"
    )


def test_refresh_randomness_and_hashing() -> None:
    tokens = {generate_refresh_token() for _ in range(100)}
    assert len(tokens) == 100
    for token in tokens:
        hashed = hash_refresh_token(token)
        assert len(token) == 64 and len(hashed) == 64
        assert hashed != token
        assert hash_refresh_token(token) == hashed


@pytest.mark.parametrize(
    "key,value",
    [
        ("JWT_SECRET_KEY", "short"),
        ("JWT_ALGORITHM", "none"),
        ("ACCESS_TOKEN_EXPIRE_MINUTES", "0"),
        ("AUTH_COOKIE_NAME", "bad;name"),
    ],
)
def test_invalid_auth_configuration(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError):
        Settings()


def test_required_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(_env_file=None)


def test_production_cookie_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    with pytest.raises(ValidationError, match="randomly generated"):
        Settings()
    monkeypatch.setenv("JWT_SECRET_KEY", generate_refresh_token())
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings()
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("SERP_PROVIDER", "serpapi")
    monkeypatch.setenv("SERPAPI_API_KEY", "mock-test-key")
    monkeypatch.setenv("SERP_ENABLED_PROVIDERS", "serpapi")
    monkeypatch.setenv("TASK_QUEUE_PROVIDER", "cloud_tasks")
    monkeypatch.setenv("GCP_PROJECT_ID", "test")
    monkeypatch.setenv("GCP_LOCATION", "test")
    monkeypatch.setenv("CLOUD_TASKS_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL", "tasks@test.example")
    monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT_EMAIL", "scheduler@test.example")
    monkeypatch.setenv("REPORT_STORAGE_PROVIDER", "gcs")
    monkeypatch.setenv("REPORT_STORAGE_BUCKET", "private-report-artifacts")
    assert Settings().auth_cookie_secure


def test_samesite_none_requires_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "none")
    with pytest.raises(ValidationError, match="SameSite=None"):
        Settings()
