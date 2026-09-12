import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_configuration_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "configuration-test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    settings = Settings()
    assert settings.app_name == "configuration-test"
    assert settings.debug is False
    assert settings.cors_origins == ["http://localhost:3000"]
    assert settings.database_url.get_secret_value() not in repr(settings)
    assert settings.serp_default_result_limit == 10
    assert settings.serp_manual_project_keyword_limit == 25


def test_multi_provider_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERP_ENABLED_PROVIDERS", "serper, serpapi")
    monkeypatch.setenv("SERP_PROVIDER_STRATEGY", "priority")
    monkeypatch.setenv("SERP_PROVIDER_PRIORITY", "serper,serpapi")
    monkeypatch.setenv("SERPER_REQUEST_BUDGET", "2500")
    monkeypatch.setenv("SERPAPI_REQUEST_BUDGET", "")
    settings = Settings()
    assert settings.enabled_provider_names == ("serper", "serpapi")
    assert settings.provider_priority_names == ("serper", "serpapi")
    assert settings.effective_provider_strategy == "priority"
    assert settings.serper_request_budget == 2500
    assert settings.serpapi_request_budget is None


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("SERP_ENABLED_PROVIDERS", "serper,unknown", "unknown providers"),
        ("SERP_PROVIDER_PRIORITY", "serper,serper", "duplicate providers"),
        ("SERP_PROVIDER_PRIORITY", "", "at least one provider"),
    ],
)
def test_invalid_provider_lists_are_rejected(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str, message: str
) -> None:
    monkeypatch.setenv("SERP_ENABLED_PROVIDERS", "serper")
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError, match=message):
        Settings()


def test_required_configuration_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_production_rejects_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings()


def test_production_rejects_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("SERP_PROVIDER", "fake")
    monkeypatch.setenv(
        "JWT_SECRET_KEY", "production-secret-with-enough-random-characters-92741"
    )
    with pytest.raises(ValidationError, match="fake SERP provider"):
        Settings()


@pytest.mark.parametrize("origins", ['["*"]', '["https://example.com/path"]'])
def test_rejects_invalid_origins(monkeypatch: pytest.MonkeyPatch, origins: str) -> None:
    monkeypatch.setenv("CORS_ORIGINS", origins)
    with pytest.raises(ValidationError, match="explicit HTTP"):
        Settings()


@pytest.mark.parametrize("key", ["DATABASE_URL", "REDIS_URL"])
def test_invalid_url_does_not_expose_input(
    monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    monkeypatch.setenv(key, "invalid://secret-password@example.com")
    with pytest.raises(ValidationError) as error:
        Settings()
    assert "secret-password" not in str(error.value)
