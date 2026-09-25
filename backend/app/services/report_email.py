import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings


class ReportEmailError(Exception):
    def __init__(self, code: str, *, transient: bool) -> None:
        super().__init__(code)
        self.code = code
        self.transient = transient


@dataclass(frozen=True)
class ReportEmail:
    recipient: str
    subject: str
    body: str
    filename: str
    mime_type: str
    attachment: bytes


class ReportEmailSender(Protocol):
    configured: bool

    async def send(self, message: ReportEmail) -> str: ...


class DisabledReportEmailSender:
    configured = False

    async def send(self, message: ReportEmail) -> str:
        raise ReportEmailError("REPORT_DELIVERY_UNAVAILABLE", transient=False)


class FakeReportEmailSender:
    configured = True

    def __init__(self) -> None:
        self.messages: list[ReportEmail] = []

    async def send(self, message: ReportEmail) -> str:
        self.messages.append(message)
        return f"fake-{uuid4()}"


class SMTPReportEmailSender:
    configured = True

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: ReportEmail) -> str:
        settings = self.settings
        email = EmailMessage()
        email["From"] = settings.report_email_from
        email["To"] = message.recipient
        email["Subject"] = message.subject
        email.set_content(message.body)
        major, minor = message.mime_type.split("/", 1)
        email.add_attachment(
            message.attachment,
            maintype=major,
            subtype=minor,
            filename=message.filename,
        )

        def deliver() -> None:
            try:
                with smtplib.SMTP(
                    settings.report_smtp_host,
                    settings.report_smtp_port,
                    timeout=15,
                ) as client:
                    if settings.report_smtp_starttls:
                        client.starttls()
                    if settings.report_smtp_username:
                        assert settings.report_smtp_password is not None
                        client.login(
                            settings.report_smtp_username,
                            settings.report_smtp_password.get_secret_value(),
                        )
                    client.send_message(email)
            except smtplib.SMTPRecipientsRefused:
                raise ReportEmailError(
                    "REPORT_RECIPIENT_REJECTED", transient=False
                ) from None
            except (OSError, smtplib.SMTPException):
                raise ReportEmailError(
                    "REPORT_DELIVERY_FAILED", transient=True
                ) from None

        await asyncio.to_thread(deliver)
        return email.get("Message-ID") or f"smtp-{uuid4()}"


def create_report_email_sender(settings: Settings) -> ReportEmailSender:
    if settings.report_email_provider == "fake":
        return FakeReportEmailSender()
    if settings.report_email_provider == "smtp":
        return SMTPReportEmailSender(settings)
    return DisabledReportEmailSender()
