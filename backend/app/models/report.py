from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportType(StrEnum):
    COMPARISON_CSV = "comparison_csv"
    HISTORY_CSV = "history_csv"
    PROJECT_PDF = "project_pdf"


class ReportStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('comparison_csv','history_csv','project_pdf')",
            name="report_type_valid",
        ),
        CheckConstraint(
            "status IN ('pending','queued','running','ready','failed','expired')",
            name="report_status_valid",
        ),
        CheckConstraint(
            "period_end_utc > period_start_utc", name="report_period_valid"
        ),
        CheckConstraint("attempt_count >= 0", name="report_attempt_count_nonnegative"),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 10", name="report_max_attempts_valid"
        ),
        CheckConstraint(
            "byte_size IS NULL OR byte_size >= 0", name="report_byte_size_valid"
        ),
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        Index("ix_generated_reports_user_status", "user_id", "status"),
        Index(
            "ix_generated_reports_project_created",
            "project_id",
            "created_at",
            "id",
        ),
        Index("ix_generated_reports_lease", "status", "lease_expires_at"),
        Index(
            "uq_generated_reports_idempotency",
            "user_id",
            "project_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    report_schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_schedules.id", ondelete="SET NULL")
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ReportStatus.PENDING
    )
    period_start_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    filters_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    metrics_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_key: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    filename: Mapped[str | None] = mapped_column(String(255))
    task_name: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    error_code: Mapped[str | None] = mapped_column(String(100))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    worker_execution_id: Mapped[UUID | None] = mapped_column()
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReportSchedule(Base):
    __tablename__ = "report_schedules"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('weekly','monthly')", name="report_frequency_valid"
        ),
        CheckConstraint("report_timezone = 'UTC'", name="report_timezone_utc"),
        CheckConstraint("scheduled_hour BETWEEN 0 AND 23", name="report_hour_valid"),
        CheckConstraint(
            "(frequency = 'weekly' AND weekday BETWEEN 0 AND 6 AND month_day IS NULL) "
            "OR (frequency = 'monthly' AND month_day BETWEEN 1 AND 31 "
            "AND weekday IS NULL)",
            name="report_schedule_calendar_valid",
        ),
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        Index("ix_report_schedules_due", "active", "next_run_at_utc"),
        Index("ix_report_schedules_project", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReportType.PROJECT_PDF
    )
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    report_timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC"
    )
    scheduled_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday: Mapped[int | None] = mapped_column(Integer)
    month_day: Mapped[int | None] = mapped_column(Integer)
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_run_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_delivery_status: Mapped[str | None] = mapped_column(String(32))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReportDeliveryAttempt(Base):
    __tablename__ = "report_delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','sent','failed','unavailable')",
            name="report_delivery_status_valid",
        ),
        CheckConstraint("attempt_number >= 1", name="report_delivery_attempt_positive"),
        UniqueConstraint(
            "generated_report_id",
            "recipient_digest",
            "attempt_number",
            name="uq_report_delivery_attempt",
        ),
        Index("ix_report_delivery_report", "generated_report_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generated_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_reports.id", ondelete="CASCADE"), nullable=False
    )
    report_schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_schedules.id", ondelete="SET NULL")
    )
    recipient_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_delivery_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
