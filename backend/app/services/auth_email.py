import asyncio
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings


class AuthEmailError(Exception):
    def __init__(self, code: str, *, transient: bool = True) -> None:
        super().__init__(code)
        self.transient = transient


@dataclass(frozen=True)
class VerificationEmail:
    recipient: str = field(repr=False)
    url: str = field(repr=False)
    expire_minutes: int


@dataclass(frozen=True)
class PasswordResetEmail:
    recipient: str = field(repr=False)
    url: str = field(repr=False)
    expire_minutes: int


class AuthEmailSender(Protocol):
    async def send(self, message: VerificationEmail | PasswordResetEmail) -> None: ...


class DisabledAuthEmailSender:
    async def send(self, message: VerificationEmail | PasswordResetEmail) -> None:
        raise AuthEmailError("AUTH_EMAIL_UNAVAILABLE")


class FakeAuthEmailSender:
    def __init__(self) -> None:
        self.messages: list[VerificationEmail | PasswordResetEmail] = []

    async def send(self, message: VerificationEmail | PasswordResetEmail) -> None:
        self.messages.append(message)


class SMTPAuthEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: VerificationEmail | PasswordResetEmail) -> None:
        settings = self.settings
        email = EmailMessage()
        email["From"] = settings.auth_email_from
        email["To"] = message.recipient
        if isinstance(message, PasswordResetEmail):
            email["Subject"] = "Reset your password | SERP SaaS"
            email.set_content(
                "A password reset was requested for your SERP SaaS account.\n\n"
                "Open this link to choose a new password:\n"
                f"{message.url}\n\n"
                f"This link expires in {message.expire_minutes} minutes "
                "and can be used once. Only the latest link will work.\n\n"
                "If you did not request this, ignore this email. "
                "Your password has not changed.\n"
                "Never share your password or this reset link."
            )
        else:
            email["Subject"] = "Verify your email address | SERP SaaS"
            email.set_content(
                "Welcome to SERP SaaS.\n\n"
                "Open this link, then select Verify email to confirm your address:\n"
                f"{message.url}\n\n"
                f"This link expires in {message.expire_minutes} minutes "
                "and can be used once.\n"
                "If you request a new email, only the latest link will work.\n\n"
                "If you did not create this account, you can ignore this email.\n"
                "Never share your password or this verification link."
            )

        await send_smtp_email(settings, email)


async def send_smtp_email(settings: Settings, email: EmailMessage) -> None:
    """Shared bounded SMTP transport for account and ranking-alert mail."""

    def deliver() -> None:
        try:
            client: smtplib.SMTP
            if settings.auth_smtp_ssl:
                client = smtplib.SMTP_SSL(
                    settings.auth_smtp_host,
                    settings.auth_smtp_port,
                    local_hostname=settings.auth_smtp_local_hostname,
                    timeout=10,
                    context=ssl.create_default_context(),
                )
            else:
                client = smtplib.SMTP(
                    settings.auth_smtp_host,
                    settings.auth_smtp_port,
                    local_hostname=settings.auth_smtp_local_hostname,
                    timeout=10,
                )
            with client:
                if settings.auth_smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                if settings.auth_smtp_username:
                    assert settings.auth_smtp_password is not None
                    client.login(
                        settings.auth_smtp_username,
                        settings.auth_smtp_password.get_secret_value(),
                    )
                client.send_message(email)
        except smtplib.SMTPRecipientsRefused:
            raise AuthEmailError(
                "AUTH_EMAIL_RECIPIENT_REJECTED", transient=False
            ) from None
        except (OSError, smtplib.SMTPException):
            raise AuthEmailError("AUTH_EMAIL_DELIVERY_FAILED") from None

    await asyncio.to_thread(deliver)


def create_auth_email_sender(settings: Settings) -> AuthEmailSender:
    if settings.auth_email_provider == "smtp":
        return SMTPAuthEmailSender(settings)
    if settings.auth_email_provider == "fake":
        return FakeAuthEmailSender()
    return DisabledAuthEmailSender()
