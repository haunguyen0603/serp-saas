"""Durable generated reports, schedules, and delivery attempts.

Revision ID: 0011_reports
Revises: 0010_keyword_organization
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_reports"
down_revision: str | None = "0010_keyword_organization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("report_timezone", sa.String(64), nullable=False),
        sa.Column("scheduled_hour", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer()),
        sa.Column("month_day", sa.Integer()),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("next_run_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at_utc", sa.DateTime(timezone=True)),
        sa.Column("last_delivery_status", sa.String(32)),
        sa.Column("last_error_code", sa.String(100)),
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
            "frequency IN ('weekly','monthly')", name="report_frequency_valid"
        ),
        sa.CheckConstraint("report_timezone = 'UTC'", name="report_timezone_utc"),
        sa.CheckConstraint("scheduled_hour BETWEEN 0 AND 23", name="report_hour_valid"),
        sa.CheckConstraint(
            "(frequency = 'weekly' AND weekday BETWEEN 0 AND 6 AND month_day IS NULL) "
            "OR (frequency = 'monthly' AND month_day BETWEEN 1 AND 31 "
            "AND weekday IS NULL)",
            name="report_schedule_calendar_valid",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_schedules_due",
        "report_schedules",
        ["active", "next_run_at_utc"],
    )
    op.create_index(
        "ix_report_schedules_project",
        "report_schedules",
        ["project_id", "created_at"],
    )

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("report_schedule_id", sa.Uuid()),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("period_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "filters_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("metrics_snapshot", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text()),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("byte_size", sa.BigInteger()),
        sa.Column("filename", sa.String(255)),
        sa.Column("task_name", sa.Text()),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("worker_execution_id", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "report_type IN ('comparison_csv','history_csv','project_pdf')",
            name="report_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending','queued','running','ready','failed','expired')",
            name="report_status_valid",
        ),
        sa.CheckConstraint(
            "period_end_utc > period_start_utc", name="report_period_valid"
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="report_attempt_count_nonnegative"
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 10", name="report_max_attempts_valid"
        ),
        sa.CheckConstraint(
            "byte_size IS NULL OR byte_size >= 0", name="report_byte_size_valid"
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_schedule_id"], ["report_schedules.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generated_reports_user_status",
        "generated_reports",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_generated_reports_project_created",
        "generated_reports",
        ["project_id", "created_at", "id"],
    )
    op.create_index(
        "ix_generated_reports_lease",
        "generated_reports",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "uq_generated_reports_idempotency",
        "generated_reports",
        ["user_id", "project_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "report_delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generated_report_id", sa.Uuid(), nullable=False),
        sa.Column("report_schedule_id", sa.Uuid()),
        sa.Column("recipient_digest", sa.String(64), nullable=False),
        sa.Column("provider_delivery_id", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending','sent','failed','unavailable')",
            name="report_delivery_status_valid",
        ),
        sa.CheckConstraint(
            "attempt_number >= 1", name="report_delivery_attempt_positive"
        ),
        sa.ForeignKeyConstraint(
            ["generated_report_id"], ["generated_reports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["report_schedule_id"], ["report_schedules.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generated_report_id",
            "recipient_digest",
            "attempt_number",
            name="uq_report_delivery_attempt",
        ),
    )
    op.create_index(
        "ix_report_delivery_report",
        "report_delivery_attempts",
        ["generated_report_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_delivery_report", table_name="report_delivery_attempts")
    op.drop_table("report_delivery_attempts")
    op.drop_index("uq_generated_reports_idempotency", table_name="generated_reports")
    op.drop_index("ix_generated_reports_lease", table_name="generated_reports")
    op.drop_index(
        "ix_generated_reports_project_created", table_name="generated_reports"
    )
    op.drop_index("ix_generated_reports_user_status", table_name="generated_reports")
    op.drop_table("generated_reports")
    op.drop_index("ix_report_schedules_project", table_name="report_schedules")
    op.drop_index("ix_report_schedules_due", table_name="report_schedules")
    op.drop_table("report_schedules")
