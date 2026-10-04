from urllib.parse import parse_qs, urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database-only settings for migrations, also shared by the application."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        url = urlsplit(value.get_secret_value())
        hosts = parse_qs(url.query).get("host", [])
        unix_socket = (
            len(hosts) == 1 and hosts[0].startswith("/") and "\x00" not in hosts[0]
        )
        if (
            url.scheme != "postgresql+asyncpg"
            or not (url.hostname or unix_socket)
            or url.path in ("", "/")
            or url.fragment
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL asyncpg URL")
        return value
