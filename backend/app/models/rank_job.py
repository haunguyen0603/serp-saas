"""Durable queue state; historical references deliberately restrict deletion."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class ProjectRankSchedule(Timestamps, Base):
    __tablename__ = "project_rank_schedules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("user_id", "project_id"),
        CheckConstraint("frequency IN ('daily', 'weekly')", name="frequency"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        Index("ix_rank_schedules_due", "enabled", "next_run_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID]
    project_id: Mapped[UUID]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(100))
    local_time: Mapped[str] = mapped_column(String(5))
    weekday: Mapped[int] = mapped_column(default=0)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RankCheckBatch(Timestamps, Base):
    __tablename__ = "rank_check_batches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "project_id", "user_id"),
        UniqueConstraint("schedule_id", "scheduled_for"),
        CheckConstraint(
            "status IN ('pending','queued','running','completed',"
            "'completed_with_errors','failed','cancelled')",
            name="status",
        ),
        CheckConstraint(
            "trigger_type IN ('manual_project','manual_keyword','scheduled')",
            name="trigger",
        ),
        CheckConstraint("requested_keyword_count >= 0", name="requested_count"),
        Index("ix_rank_batches_history", "user_id", "project_id", "created_at"),
        Index("ix_rank_batches_project_status", "project_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID]
    project_id: Mapped[UUID]
    trigger_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    requested_keyword_count: Mapped[int]
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_rank_schedules.id", ondelete="SET NULL")
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RankCheckJob(Timestamps, Base):
    __tablename__ = "rank_check_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["batch_id", "project_id", "user_id"],
            [
                "rank_check_batches.id",
                "rank_check_batches.project_id",
                "rank_check_batches.user_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("batch_id", "keyword_id"),
        CheckConstraint(
            "status IN ('pending','queued','running','succeeded','failed','cancelled')",
            name="status",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
            name="attempts",
        ),
        Index("ix_rank_jobs_batch_status", "batch_id", "status"),
        Index("ix_rank_jobs_keyword_status", "keyword_id", "status"),
        Index("ix_rank_jobs_lease", "status", "lease_expires_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    batch_id: Mapped[UUID]
    user_id: Mapped[UUID]
    project_id: Mapped[UUID]
    keyword_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempt_count: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int]
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_execution_id: Mapped[UUID | None]
    rank_check_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="RESTRICT"), unique=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    task_name: Mapped[str | None] = mapped_column(String(512))
