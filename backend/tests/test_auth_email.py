import smtplib
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.services.auth_email import (
    AuthEmailError,
    SMTPAuthEmailSender,
    VerificationEmail,
)


@pytest.mark.parametrize("ssl_mode", [False, True])
@pytest.mark.parametrize("hostname", ["app.serpsaas.com", "mail.client.example"])
async def test_smtp_tls_credentials_and_message(
    settings, monkeypatch, ssl_mode, hostname
):
    settings = settings.model_copy(
        update={
            "auth_email_from": "SERP SaaS <noreply@example.com>",
            "auth_smtp_host": "smtp.example.com",
            "auth_smtp_local_hostname": hostname,
            "auth_smtp_port": 465 if ssl_mode else 587,
            "auth_smtp_ssl": ssl_mode,
            "auth_smtp_starttls": not ssl_mode,
            "auth_smtp_username": "smtp-user",
            "auth_smtp_password": SecretStr("smtp-password"),
        }
    )
    connection = MagicMock()
    connection.__enter__.return_value = connection
    constructor = MagicMock(return_value=connection)
    monkeypatch.setattr(smtplib, "SMTP_SSL" if ssl_mode else "SMTP", constructor)
    await SMTPAuthEmailSender(settings).send(
        VerificationEmail(
            "person@example.com",
            "https://app.example.com/verify-email#token=test-token",
            60,
        )
    )
    connection.login.assert_called_once_with("smtp-user", "smtp-password")
    assert constructor.call_args.kwargs["local_hostname"] == hostname
    assert constructor.call_args.args == (
        "smtp.example.com",
        465 if ssl_mode else 587,
    )
    if ssl_mode:
        connection.starttls.assert_not_called()
        assert constructor.call_args.kwargs["context"].check_hostname
    else:
        connection.starttls.assert_called_once()
        assert connection.starttls.call_args.kwargs["context"].check_hostname
    message = connection.send_message.call_args.args[0]
    assert message["To"] == "person@example.com"
    assert message["Subject"] == "Verify your email address | SERP SaaS"
    assert "/verify-email#token=test-token" in message.get_content()
    assert "smtp-password" not in message.as_string()


async def test_smtp_failure_is_sanitized(settings, monkeypatch):
    monkeypatch.setattr(
        smtplib,
        "SMTP",
        MagicMock(
            side_effect=smtplib.SMTPAuthenticationError(535, b"private password")
        ),
    )
    with pytest.raises(AuthEmailError, match="AUTH_EMAIL_DELIVERY_FAILED") as failure:
        await SMTPAuthEmailSender(settings).send(
            VerificationEmail(
                "person@example.com",
                "https://app.example.com/verify-email#token=test-token",
                60,
            )
        )
    assert "private password" not in str(failure.value)


def test_smtp_local_hostname_default_and_environment(settings, monkeypatch):
    values = settings.model_dump(exclude={"auth_smtp_local_hostname"})
    monkeypatch.delenv("AUTH_SMTP_LOCAL_HOSTNAME", raising=False)
    assert Settings(_env_file=None, **values).auth_smtp_local_hostname == (
        "app.serpsaas.com"
    )
    monkeypatch.setenv("AUTH_SMTP_LOCAL_HOSTNAME", "Mail.Client.Example")
    assert Settings(_env_file=None, **values).auth_smtp_local_hostname == (
        "mail.client.example"
    )


@pytest.mark.parametrize(
    "hostname",
    [
        "",
        "localhost",
        "127.0.0.1",
        "[127.0.0.1]",
        "::1",
        "https://app.serpsaas.com",
        "app.serpsaas.com:465",
        "app.serpsaas.com/path",
        "app.serpsaas.com\r\nMAIL FROM:<attacker@example.com>",
        "app.serpsaas.com\n",
        " app.serpsaas.com",
        "bad_name.example.com",
        "-app.example.com",
        "app-.example.com",
        "app..example.com",
        f"{'a' * 64}.example.com",
    ],
)
def test_smtp_local_hostname_rejects_unsafe_values(settings, hostname):
    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "auth_smtp_local_hostname": hostname})


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:secret@app.example.com",
        "https://app.example.com/path",
        "https://app.example.com?redirect=evil",
        "https://app.example.com#token=evil",
    ],
)
def test_verification_origin_rejects_unsafe_values(settings, url):
    with pytest.raises(ValidationError, match="AUTH_SITE_URL"):
        Settings(**{**settings.model_dump(), "auth_site_url": url})


def production_values(settings):
    return {
        **settings.model_dump(),
        "app_env": "production",
        "debug": False,
        "auth_cookie_secure": True,
        "jwt_secret_key": "prod-test-abcdefghijklmnopqrstuvwxyz-92741",
        "task_queue_provider": "cloud_tasks",
        "gcp_project_id": "test-project",
        "gcp_location": "asia-southeast1",
        "cloud_tasks_worker_url": "https://worker.example.com",
        "cloud_tasks_service_account_email": "tasks@test.iam.gserviceaccount.com",
        "scheduler_service_account_email": "scheduler@test.iam.gserviceaccount.com",
        "report_storage_provider": "gcs",
        "report_storage_bucket": "test-bucket",
        "auth_email_provider": "smtp",
        "auth_email_from": "noreply@example.com",
        "auth_smtp_host": "smtp.example.com",
        "auth_smtp_starttls": True,
        "auth_site_url": "https://app.example.com",
    }


def test_production_verification_configuration(settings):
    values = production_values(settings)
    assert Settings(**values).auth_site_url == "https://app.example.com"
    for change, expected in [
        ({"auth_email_provider": "fake"}, "requires SMTP"),
        ({"auth_email_provider": "disabled"}, "requires SMTP"),
        ({"auth_site_url": "http://app.example.com"}, "requires HTTPS"),
        ({"auth_smtp_starttls": False}, "requires TLS"),
        ({"auth_smtp_ssl": True}, "either auth SMTP"),
        ({"auth_smtp_username": "user"}, "configured together"),
    ]:
        with pytest.raises(ValidationError, match=expected):
            Settings(**{**values, **change})
