"""Persist one-time SePay purchases and provider events.

Revision ID: 0016_sepay_payments
Revises: 0015_vnd_pricing
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0016_sepay_payments"
down_revision = "0015_vnd_pricing"
branch_labels = None
depends_on = None


def identity() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        *identity(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_environment", sa.String(16), nullable=False),
        sa.Column("invoice_number", sa.String(64), nullable=False, unique=True),
        sa.Column("product_line", sa.String(16), nullable=False),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("plan_code", sa.String(64), nullable=False),
        sa.Column("plan_name_snapshot", sa.String(120), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("commercial_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider_order_id", sa.String(200)),
        sa.Column("provider_transaction_id", sa.String(200)),
        sa.Column("provider_transaction_uuid", sa.String(200)),
        sa.Column("payment_method", sa.String(32)),
        sa.Column("provider_order_status", sa.String(32)),
        sa.Column("provider_transaction_status", sa.String(32)),
        sa.Column("provider_payload_snapshot", postgresql.JSONB()),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("subscriptions.id")),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_minor > 0 AND currency = 'VND'", name="money"),
        sa.CheckConstraint(
            "product_line IN ('desktop', 'mobile')", name="product_line"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'checkout_created', 'paid', 'failed', 'cancelled', "
            "'voided', 'expired', 'review_required')",
            name="status",
        ),
    )
    op.create_index(
        "ix_payment_orders_user_created", "payment_orders", ["user_id", "created_at"]
    )
    op.create_index("ix_payment_orders_status", "payment_orders", ["status"])
    op.create_index(
        "uq_payment_orders_provider_order",
        "payment_orders",
        ["provider", "provider_environment", "provider_order_id"],
        unique=True,
    )
    for suffix, column in (
        ("transaction", "provider_transaction_id"),
        ("transaction_uuid", "provider_transaction_uuid"),
    ):
        op.create_index(
            f"uq_payment_orders_provider_{suffix}",
            "payment_orders",
            ["provider", "provider_environment", column],
            unique=True,
        )
    op.create_table(
        "payment_events",
        *identity(),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False, unique=True),
        sa.Column("notification_type", sa.String(64), nullable=False),
        sa.Column("payment_order_id", sa.Uuid(), sa.ForeignKey("payment_orders.id")),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_result", sa.String(64), nullable=False),
    )
    op.create_index("ix_payment_events_order", "payment_events", ["payment_order_id"])


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("payment_orders")
