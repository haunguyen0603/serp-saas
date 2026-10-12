"""Immutable purchase terms and minimized provider reconciliation evidence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.billing import IdentityTime


class PaymentOrder(IdentityTime, Base):
    __tablename__ = "payment_orders"
    __table_args__ = (
        CheckConstraint("amount_minor > 0 AND currency = 'VND'", name="money"),
        CheckConstraint("product_line IN ('desktop', 'mobile')", name="product_line"),
        CheckConstraint(
            "status IN ('pending', 'checkout_created', 'paid', 'failed', 'cancelled', "
            "'voided', 'expired', 'review_required')",
            name="status",
        ),
        Index("ix_payment_orders_user_created", "user_id", "created_at"),
        Index("ix_payment_orders_status", "status"),
        Index(
            "uq_payment_orders_provider_order",
            "provider",
            "provider_environment",
            "provider_order_id",
            unique=True,
        ),
        Index(
            "uq_payment_orders_provider_transaction",
            "provider",
            "provider_environment",
            "provider_transaction_id",
            unique=True,
        ),
        Index(
            "uq_payment_orders_provider_transaction_uuid",
            "provider",
            "provider_environment",
            "provider_transaction_uuid",
            unique=True,
        ),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(32), default="sepay")
    provider_environment: Mapped[str] = mapped_column(String(16))
    invoice_number: Mapped[str] = mapped_column(String(64), unique=True)
    product_line: Mapped[str] = mapped_column(String(16))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"))
    plan_code: Mapped[str] = mapped_column(String(64))
    plan_name_snapshot: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3))
    amount_minor: Mapped[int] = mapped_column(Integer)
    commercial_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    provider_order_id: Mapped[str | None] = mapped_column(String(200))
    provider_transaction_id: Mapped[str | None] = mapped_column(String(200))
    provider_transaction_uuid: Mapped[str | None] = mapped_column(String(200))
    payment_method: Mapped[str | None] = mapped_column(String(32))
    provider_order_status: Mapped[str | None] = mapped_column(String(32))
    provider_transaction_status: Mapped[str | None] = mapped_column(String(32))
    provider_payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    subscription_id: Mapped[UUID | None] = mapped_column(ForeignKey("subscriptions.id"))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PaymentEvent(IdentityTime, Base):
    __tablename__ = "payment_events"
    __table_args__ = (Index("ix_payment_events_order", "payment_order_id"),)
    provider: Mapped[str] = mapped_column(String(32))
    event_key: Mapped[str] = mapped_column(String(64), unique=True)
    notification_type: Mapped[str] = mapped_column(String(64))
    payment_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payment_orders.id")
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_result: Mapped[str] = mapped_column(String(64))
