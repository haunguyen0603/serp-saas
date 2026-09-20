"""Audit administrator changes to the Plan catalog.

Revision ID: 0009_plan_catalog_audit
Revises: 0008_billing_usage_limits
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_plan_catalog_audit"
down_revision = "0008_billing_usage_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=False),
        sa.Column("after", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_changes_created", "plan_changes", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_plan_changes_created", table_name="plan_changes")
    op.drop_table("plan_changes")
