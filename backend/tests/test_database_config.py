from urllib.parse import quote

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.database_config import DatabaseSettings

SOCKET = "/cloudsql/serp-saas:asia-southeast1:serp-saas"


def test_cloud_sql_socket_and_encoded_password(monkeypatch: pytest.MonkeyPatch) -> None:
    password = "test@:/?#%+password"
    url = (
        f"postgresql+asyncpg://serp_app:{quote(password, safe='')}@/serp_saas"
        f"?host={SOCKET}&ssl=disable"
    )
    monkeypatch.setenv("DATABASE_URL", url)
    assert Settings().database_url.get_secret_value() == url
    settings = DatabaseSettings(_env_file=None)
    engine = create_async_engine(settings.database_url.get_secret_value())
    _, arguments = engine.dialect.create_connect_args(engine.url)
    assert arguments["host"] == SOCKET
    assert arguments["user"] == "serp_app"
    assert arguments["database"] == "serp_saas"
    assert arguments["password"] == password
    assert password not in repr(settings)
    assert url not in repr(settings)


def test_database_only_settings_ignore_missing_runtime_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:test@localhost/db")
    assert DatabaseSettings(_env_file=None).database_url.get_secret_value()
    # Runtime still enforces its full configuration independently of migration.
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://app:private-test-password@localhost/db",
        "postgresql+asyncpg://app:private-test-password@/db",
        "postgresql+asyncpg://app:private-test-password@/db?host=relative/path",
        "postgresql+asyncpg://app:private-test-password@/db?host=/one&host=/two",
        "postgresql+asyncpg://app:private-test-password@/db?host=/%00",
        "postgresql+asyncpg://app:private-test-password@localhost/",
        "postgresql+asyncpg://app:private-test-password@localhost/db#fragment",
    ],
)
def test_invalid_database_url_is_redacted(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(_env_file=None)
    assert "private-test-password" not in str(error.value)
