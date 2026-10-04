from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from app.core.database_config import DatabaseSettings


class Settings(DatabaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    app_name: str = Field(min_length=1)
    app_version: str = Field(min_length=1)
    app_env: Literal["development", "test", "production"]
    debug: bool
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    redis_url: SecretStr
    cors_origins: list[str]
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)
    auth_cookie_name: str = Field(
        default="serp_refresh_token", pattern=r"^[A-Za-z0-9_]+$"
    )
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_require_verified_email: bool = True
    auth_site_url: str = "http://localhost:3000"
    auth_verification_expire_minutes: int = Field(default=60, ge=5, le=1440)
    auth_verification_resend_seconds: int = Field(default=60, ge=10, le=3600)
    auth_verification_max_emails_per_hour: int = Field(default=5, ge=1, le=20)
    auth_email_provider: Literal["disabled", "fake", "smtp"] = "disabled"
    auth_email_from: str = ""
    auth_smtp_host: str = ""
    auth_smtp_port: int = Field(default=587, ge=1, le=65535)
    auth_smtp_username: str = ""
    auth_smtp_password: SecretStr | None = None
    auth_smtp_starttls: bool = True
    auth_smtp_ssl: bool = False
    # SERP_PROVIDER remains as a compatibility fallback for existing M4 installs.
    serp_provider: Literal["serpapi", "serper", "fake"] = "serpapi"
    serp_enabled_providers: str | None = None
    serp_provider_strategy: Literal["fixed", "priority"] = "priority"
    serp_provider_priority: str = "serper,serpapi"
    serp_fixed_provider: Literal["serpapi", "serper", "fake"] | None = None
    serp_max_provider_fallbacks: int = Field(default=1, ge=0, le=10)
    serpapi_api_key: SecretStr | None = None
    serpapi_base_url: str = "https://serpapi.com/search"
    serpapi_request_budget: int | None = Field(default=None, ge=1)
    serper_api_key: SecretStr | None = None
    serper_base_url: str = "https://google.serper.dev/search"
    serper_request_budget: int | None = Field(default=None, ge=1)
    serp_request_timeout_seconds: float = Field(default=10.0, ge=0.1, le=60)
    serp_default_result_limit: int = Field(default=10, ge=1, le=100)
    serp_max_concurrent_requests: int = Field(default=3, ge=1, le=10)
    serp_manual_project_keyword_limit: int = Field(default=25, ge=1, le=100)

    task_queue_provider: Literal["local", "cloud_tasks"] = "local"
    gcp_project_id: str = ""
    gcp_location: str = ""
    cloud_tasks_queue: str = "rank-checks"
    cloud_tasks_worker_url: str = ""
    cloud_tasks_service_account_email: str = ""
    scheduler_service_account_email: str = ""
    rank_check_batch_max_keywords: int = Field(default=5000, ge=1, le=5000)
    rank_check_job_max_attempts: int = Field(default=5, ge=1, le=10)
    rank_check_job_lease_seconds: int = Field(default=300, ge=30, le=1800)
    task_dispatch_max_per_second: float = Field(default=2, gt=0)
    task_max_concurrent_dispatches: int = Field(default=2, ge=1)
    task_min_backoff_seconds: int = Field(default=30, ge=1)
    task_max_backoff_seconds: int = Field(default=300, ge=1)
    task_max_retry_duration_seconds: int = Field(default=3600, ge=60)
    worker_db_pool_size: int = Field(default=2, ge=1, le=10)
    worker_db_max_overflow: int = Field(default=0, ge=0, le=10)

    report_max_range_days: int = Field(default=365, ge=1, le=3660)
    report_max_csv_rows: int = Field(default=100000, ge=1, le=1000000)
    report_max_pdf_detail_rows: int = Field(default=1000, ge=1, le=10000)
    report_artifact_retention_days: int = Field(default=30, ge=1, le=365)
    report_max_concurrent_per_user: int = Field(default=2, ge=1, le=20)
    report_max_active_schedules_per_project: int = Field(default=5, ge=1, le=50)
    report_job_max_attempts: int = Field(default=3, ge=1, le=10)
    report_job_lease_seconds: int = Field(default=300, ge=30, le=1800)
    report_storage_provider: Literal["local", "gcs"] = "local"
    report_storage_root: str = "/tmp/serp-saas-reports"
    report_storage_bucket: str = ""
    report_storage_prefix: str = "reports"
    report_email_provider: Literal["disabled", "fake", "smtp"] = "disabled"
    report_email_from: str = ""
    report_email_attachment_max_bytes: int = Field(
        default=5_000_000, ge=100_000, le=25_000_000
    )
    report_smtp_host: str = ""
    report_smtp_port: int = Field(default=587, ge=1, le=65535)
    report_smtp_username: str = ""
    report_smtp_password: SecretStr | None = None
    report_smtp_starttls: bool = True

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
        return value

    @field_validator("auth_site_url")
    @classmethod
    def validate_auth_site_url(cls, value: str) -> str:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("AUTH_SITE_URL must be an explicit HTTP(S) origin")
        return value.rstrip("/")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: SecretStr) -> SecretStr:
        url = urlsplit(value.get_secret_value())
        if url.scheme not in {"redis", "rediss"} or not url.hostname:
            raise ValueError("REDIS_URL must be a Redis URL")
        return value

    @field_validator("serpapi_base_url", "serper_base_url")
    @classmethod
    def validate_serpapi_base_url(cls, value: str) -> str:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.fragment
        ):
            raise ValueError("SERP provider base URLs must be HTTP(S) URLs")
        return value

    @field_validator(
        "serpapi_request_budget",
        "serper_request_budget",
        mode="before",
    )
    @classmethod
    def empty_optional_integer(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("serp_fixed_provider", mode="before")
    @classmethod
    def empty_optional_provider(cls, value: object) -> object:
        return None if value == "" else value

    @staticmethod
    def _provider_names(value: str, field: str) -> tuple[str, ...]:
        names = tuple(part.strip().lower() for part in value.split(",") if part.strip())
        if not names:
            raise ValueError(f"{field} must contain at least one provider")
        if len(names) != len(set(names)):
            raise ValueError(f"{field} must not contain duplicate providers")
        unknown = set(names) - {"serper", "serpapi", "fake"}
        if unknown:
            raise ValueError(
                f"{field} contains unknown providers: {', '.join(sorted(unknown))}"
            )
        return names

    @property
    def enabled_provider_names(self) -> tuple[str, ...]:
        if (
            self.serp_enabled_providers is None
            or not self.serp_enabled_providers.strip()
        ):
            return (self.serp_provider,)
        return self._provider_names(
            self.serp_enabled_providers, "SERP_ENABLED_PROVIDERS"
        )

    @property
    def provider_priority_names(self) -> tuple[str, ...]:
        return self._provider_names(
            self.serp_provider_priority, "SERP_PROVIDER_PRIORITY"
        )

    @property
    def effective_provider_strategy(self) -> Literal["fixed", "priority"]:
        if (
            self.serp_enabled_providers is None
            or not self.serp_enabled_providers.strip()
        ):
            return "fixed"
        return self.serp_provider_strategy

    @property
    def effective_fixed_provider(self) -> str:
        return self.serp_fixed_provider or self.serp_provider

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
                or url.path
                or url.query
                or url.fragment
                or "*" in origin
            ):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return origins

    @model_validator(mode="after")
    def validate_production(self) -> Self:
        enabled = self.enabled_provider_names
        priority = self.provider_priority_names
        if self.effective_provider_strategy == "fixed":
            if self.effective_fixed_provider not in enabled:
                raise ValueError("SERP_FIXED_PROVIDER must be enabled")
        elif not set(priority).intersection(enabled):
            raise ValueError("SERP_PROVIDER_PRIORITY must include an enabled provider")
        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false in production")
        if self.app_env == "production":
            secret = self.jwt_secret_key.get_secret_value().lower()
            if (
                any(
                    marker in secret
                    for marker in ("placeholder", "change-me", "development")
                )
                or len(set(secret)) < 16
            ):
                raise ValueError(
                    "Production requires a randomly generated JWT_SECRET_KEY"
                )
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
            if "fake" in enabled:
                raise ValueError("The fake SERP provider is not allowed in production")
            configured = {
                "serper": bool(
                    self.serper_api_key and self.serper_api_key.get_secret_value()
                ),
                "serpapi": bool(
                    self.serpapi_api_key and self.serpapi_api_key.get_secret_value()
                ),
            }
            if not any(configured.get(name, False) for name in enabled):
                raise ValueError(
                    "Production requires at least one configured enabled SERP provider"
                )
            if self.effective_provider_strategy == "fixed" and not configured.get(
                self.effective_fixed_provider, False
            ):
                raise ValueError(
                    "Production fixed strategy requires its provider credentials"
                )
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError("SameSite=None requires AUTH_COOKIE_SECURE=true")
        return self

    @model_validator(mode="after")
    def validate_queue(self) -> Self:
        if self.app_env == "production" and self.task_queue_provider != "cloud_tasks":
            raise ValueError("Production requires Cloud Tasks")
        if self.task_queue_provider == "cloud_tasks":
            if not all(
                (
                    self.gcp_project_id,
                    self.gcp_location,
                    self.cloud_tasks_worker_url,
                    self.cloud_tasks_service_account_email,
                    self.scheduler_service_account_email,
                )
            ):
                raise ValueError(
                    "Cloud Tasks and internal OIDC configuration is required"
                )
            url = urlsplit(self.cloud_tasks_worker_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.path not in ("", "/")
                or url.query
                or url.fragment
                or url.username
            ):
                raise ValueError("Worker URL must be an HTTPS service origin")
        return self

    @model_validator(mode="after")
    def validate_reporting(self) -> Self:
        if not self.report_storage_root.strip():
            raise ValueError("REPORT_STORAGE_ROOT must not be empty")
        if self.report_storage_provider == "gcs" and not self.report_storage_bucket:
            raise ValueError("GCS report storage requires REPORT_STORAGE_BUCKET")
        if self.app_env == "production" and self.report_storage_provider != "gcs":
            raise ValueError("Production report storage requires GCS")
        if not self.report_storage_prefix.strip().strip("/"):
            raise ValueError("REPORT_STORAGE_PREFIX must not be empty")
        if self.report_email_provider == "fake" and self.app_env == "production":
            raise ValueError("Fake report email delivery is not allowed in production")
        if self.report_email_provider == "smtp":
            if not self.report_smtp_host or not self.report_email_from:
                raise ValueError(
                    "SMTP report delivery requires REPORT_SMTP_HOST and "
                    "REPORT_EMAIL_FROM"
                )
            if bool(self.report_smtp_username) != bool(
                self.report_smtp_password
                and self.report_smtp_password.get_secret_value()
            ):
                raise ValueError(
                    "REPORT_SMTP_USERNAME and REPORT_SMTP_PASSWORD must be "
                    "configured together"
                )
        return self

    @model_validator(mode="after")
    def validate_auth_email(self) -> Self:
        if self.auth_email_provider == "smtp":
            if not self.auth_smtp_host or not self.auth_email_from:
                raise ValueError(
                    "Auth SMTP requires AUTH_SMTP_HOST and AUTH_EMAIL_FROM"
                )
            if any(c in self.auth_email_from for c in "\r\n"):
                raise ValueError("AUTH_EMAIL_FROM must not contain newlines")
            if self.auth_smtp_starttls and self.auth_smtp_ssl:
                raise ValueError("Choose either auth SMTP STARTTLS or implicit SSL")
            if bool(self.auth_smtp_username) != bool(
                self.auth_smtp_password and self.auth_smtp_password.get_secret_value()
            ):
                raise ValueError(
                    "Auth SMTP username and password must be configured together"
                )
        if self.app_env == "production":
            if self.auth_email_provider != "smtp":
                raise ValueError("Production email verification requires SMTP")
            if not self.auth_site_url.startswith("https://"):
                raise ValueError("Production AUTH_SITE_URL requires HTTPS")
            if not (self.auth_smtp_starttls or self.auth_smtp_ssl):
                raise ValueError("Production auth SMTP requires TLS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
