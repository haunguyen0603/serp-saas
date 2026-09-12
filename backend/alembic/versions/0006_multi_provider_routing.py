"""Persist provider usage and Rank Check provider attempts."""

import sqlalchemy as sa

from alembic import op

revision: str = "0006_multi_provider_routing"
down_revision: str | None = "0005_rank_tracking"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "provider_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column(
            "period_type", sa.String(16), server_default="monthly", nullable=False
        ),
        sa.Column("period_key", sa.String(7), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fallback_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.CheckConstraint(
            "request_count >= 0", name="ck_provider_usage_request_count"
        ),
        sa.CheckConstraint(
            "success_count >= 0", name="ck_provider_usage_success_count"
        ),
        sa.CheckConstraint(
            "failure_count >= 0", name="ck_provider_usage_failure_count"
        ),
        sa.CheckConstraint(
            "fallback_count >= 0", name="ck_provider_usage_fallback_count"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "period_type", "period_key", name="uq_provider_usage_period"
        ),
    )
    op.create_index(
        "ix_provider_usage_provider_period_key",
        "provider_usage",
        ["provider", "period_key"],
    )
    op.create_table(
        "rank_check_provider_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rank_check_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "succeeded",
                "failed",
                name="provider_attempt_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("provider_request_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_number >= 1",
            name="ck_rank_check_provider_attempts_attempt_number_positive",
        ),
        sa.CheckConstraint(
            "provider_request_count >= 1",
            name="ck_rank_check_provider_attempts_request_count_positive",
        ),
        sa.ForeignKeyConstraint(
            ["rank_check_id"],
            ["rank_checks.id"],
            name="fk_provider_attempts_rank_check_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rank_check_id", "attempt_number", name="uq_provider_attempt_check_number"
        ),
    )
    op.create_index(
        "ix_provider_attempt_check_number",
        "rank_check_provider_attempts",
        ["rank_check_id", "attempt_number"],
    )
    op.create_index(
        "ix_provider_attempt_provider_created_at",
        "rank_check_provider_attempts",
        ["provider", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_attempt_provider_created_at",
        table_name="rank_check_provider_attempts",
    )
    op.drop_index(
        "ix_provider_attempt_check_number", table_name="rank_check_provider_attempts"
    )
    op.drop_table("rank_check_provider_attempts")
    op.drop_index("ix_provider_usage_provider_period_key", table_name="provider_usage")
    op.drop_table("provider_usage")
