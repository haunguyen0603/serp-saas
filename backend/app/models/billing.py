"""Device-scoped commercial terms and logical usage ledger."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
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


class IdentityTime:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Plan(IdentityTime, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("device_scope IN ('desktop', 'mobile')", name="device_scope"),
        CheckConstraint(
            "price_monthly_minor_units >= 0 AND max_projects >= 0 "
            "AND max_keywords >= 0 AND monthly_keyword_checks >= 0",
            name="nonnegative_terms",
        ),
        CheckConstraint(
            "max_scheduled_frequency IN ('none', 'weekly', 'daily')", name="frequency"
        ),
        Index("ix_plans_catalog", "device_scope", "active", "display_order"),
    )
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    device_scope: Mapped[str] = mapped_column(String(16))
    price_monthly_minor_units: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    max_projects: Mapped[int] = mapped_column(Integer)
    max_keywords: Mapped[int] = mapped_column(Integer)
    monthly_keyword_checks: Mapped[int] = mapped_column(Integer)
    scheduled_checks_enabled: Mapped[bool] = mapped_column(Boolean)
    max_scheduled_frequency: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    display_order: Mapped[int] = mapped_column(Integer)


class PlanChange(IdentityTime, Base):
    __tablename__ = "plan_changes"
    __table_args__ = (Index("ix_plan_changes_created", "created_at", "id"),)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    before: Mapped[dict[str, Any]] = mapped_column(JSONB)
    after: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Subscription(IdentityTime, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("device_scope IN ('desktop', 'mobile')", name="device_scope"),
        CheckConstraint(
            "status IN ('scheduled', 'active', 'expired', 'cancelled')", name="status"
        ),
        CheckConstraint("period_end > period_start", name="period"),
        Index(
            "uq_subscriptions_active_device",
            "user_id",
            "device_scope",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "ix_subscriptions_user_device_status", "user_id", "device_scope", "status"
        ),
        Index("ix_subscriptions_user_end", "user_id", "period_end"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"))
    device_scope: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    payment_method: Mapped[str | None] = mapped_column(String(32))
    payment_reference: Mapped[str | None] = mapped_column(String(200))
    payment_note: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class UsagePeriod(IdentityTime, Base):
    __tablename__ = "usage_periods"
    __table_args__ = (
        UniqueConstraint("subscription_id", "period_start"),
        CheckConstraint("period_end > period_start", name="period"),
        CheckConstraint(
            "reserved_keyword_checks >= 0 AND committed_keyword_checks >= 0 "
            "AND keyword_check_limit + adjustment >= 0",
            name="counters",
        ),
        Index(
            "ix_usage_periods_user_device_start",
            "user_id",
            "device_scope",
            "period_start",
        ),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subscription_id: Mapped[UUID] = mapped_column(ForeignKey("subscriptions.id"))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"))
    device_scope: Mapped[str] = mapped_column(String(16))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    keyword_check_limit: Mapped[int] = mapped_column(Integer)
    adjustment: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved_keyword_checks: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    committed_keyword_checks: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )


class UsageReservation(IdentityTime, Base):
    __tablename__ = "usage_reservations"
    __table_args__ = (
        CheckConstraint("amount = 1", name="one_logical_job"),
        CheckConstraint(
            "status IN ('reserved', 'committed', 'released')", name="status"
        ),
        Index("ix_usage_reservations_period_status", "usage_period_id", "status"),
        Index("ix_usage_reservations_batch", "batch_id"),
    )
    usage_period_id: Mapped[UUID] = mapped_column(ForeignKey("usage_periods.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    device_scope: Mapped[str] = mapped_column(String(16))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("rank_check_batches.id"))
    job_id: Mapped[UUID] = mapped_column(ForeignKey("rank_check_jobs.id"), unique=True)
    amount: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[str] = mapped_column(
        String(16), default="reserved", server_default="reserved"
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageEvent(IdentityTime, Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('commit', 'release', 'adjustment')", name="event_type"
        ),
        UniqueConstraint("reservation_id"),
    )
    usage_period_id: Mapped[UUID] = mapped_column(ForeignKey("usage_periods.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    device_scope: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[int] = mapped_column(Integer)
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("rank_check_jobs.id"))
    batch_id: Mapped[UUID | None] = mapped_column(ForeignKey("rank_check_batches.id"))
    reservation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("usage_reservations.id")
    )


class BillingAuditEvent(IdentityTime, Base):
    __tablename__ = "billing_audit_events"
    __table_args__ = (
        Index("ix_billing_audit_target_created", "target_user_id", "created_at"),
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    target_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(64))
    device_scope: Mapped[str] = mapped_column(String(16))
    subscription_id: Mapped[UUID | None] = mapped_column(ForeignKey("subscriptions.id"))
    plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("plans.id"))
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
