"""Ranking-only inbox and durable evaluation/email outboxes."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
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


class RankingAlertPreference(Base):
    __tablename__ = "ranking_alert_preferences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "user_id", "project_id", name="uq_ranking_alert_preferences_owner"
        ),
        CheckConstraint("movement_threshold BETWEEN 1 AND 10", name="threshold"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID]
    project_id: Mapped[UUID]
    enabled: Mapped[bool] = mapped_column(default=True, server_default="true")
    notify_entered_top10: Mapped[bool] = mapped_column(
        default=True, server_default="true"
    )
    notify_left_top10: Mapped[bool] = mapped_column(default=True, server_default="true")
    notify_improvement: Mapped[bool] = mapped_column(
        default=True, server_default="true"
    )
    notify_decline: Mapped[bool] = mapped_column(default=True, server_default="true")
    movement_threshold: Mapped[int] = mapped_column(default=3, server_default="3")
    email_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RankingAlertEvaluation(Base):
    __tablename__ = "ranking_alert_evaluations"
    __table_args__ = (
        Index("ix_ranking_alert_evaluations_pending", "status", "next_attempt_at"),
        Index(
            "ix_ranking_alert_evaluations_history",
            "keyword_id",
            "observed_at",
            "check_id",
        ),
        CheckConstraint("status IN ('pending','completed','failed')", name="status"),
        CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts"),
    )
    check_id: Mapped[UUID] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="RESTRICT"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT")
    )
    keyword_id: Mapped[UUID] = mapped_column(
        ForeignKey("keywords.id", ondelete="RESTRICT")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    suppressed: Mapped[bool] = mapped_column(default=False, server_default="false")
    environment: Mapped[str] = mapped_column(String(64))
    # All active matching identities (including unmatched sites) at persistence time.
    sites: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RankingAlert(Base):
    __tablename__ = "ranking_alerts"
    __table_args__ = (
        UniqueConstraint(
            "current_observation_id",
            "site_identity",
            "alert_type",
            name="uq_ranking_alert_event",
        ),
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "alert_type IN ('entered_top10','left_top10',"
            "'rank_improved','rank_declined')",
            name="type",
        ),
        CheckConstraint(
            "previous_rank IS NULL OR previous_rank BETWEEN 1 AND 10",
            name="previous_rank",
        ),
        CheckConstraint(
            "current_rank IS NULL OR current_rank BETWEEN 1 AND 10", name="current_rank"
        ),
        CheckConstraint(
            "previous_rank IS NOT NULL OR current_rank IS NOT NULL",
            name="rank_transition",
        ),
        Index(
            "ix_ranking_alerts_inbox",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_ranking_alerts_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
        Index("ix_ranking_alerts_project", "project_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID]
    project_id: Mapped[UUID]
    keyword_id: Mapped[UUID]
    tracked_site_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tracked_sites.id", ondelete="SET NULL")
    )
    site_identity: Mapped[UUID]  # Immutable even after site deletion.
    alert_type: Mapped[str] = mapped_column(String(32))
    previous_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="RESTRICT")
    )
    current_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="RESTRICT")
    )
    previous_rank: Mapped[int | None] = mapped_column(Integer)
    current_rank: Mapped[int | None] = mapped_column(Integer)
    rank_delta: Mapped[int | None] = mapped_column(Integer)
    keyword: Mapped[str] = mapped_column(Text)
    project_name: Mapped[str] = mapped_column(String(200))
    site_name: Mapped[str] = mapped_column(String(200))
    device: Mapped[str] = mapped_column(String(16))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RankingAlertDelivery(Base):
    __tablename__ = "ranking_alert_deliveries"
    __table_args__ = (
        UniqueConstraint("alert_id", "channel", name="uq_ranking_alert_delivery"),
        CheckConstraint("channel = 'email'", name="channel"),
        CheckConstraint(
            "status IN ('pending','sending','sent','suppressed','failed')",
            name="status",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts"),
        Index("ix_ranking_alert_deliveries_pending", "status", "next_attempt_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_alerts.id", ondelete="RESTRICT")
    )
    channel: Mapped[str] = mapped_column(
        String(16), default="email", server_default="email"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(String(64))
