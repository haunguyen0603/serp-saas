"""ranking_alerts

Revision ID: 0017_ranking_alerts
Revises: 0016_sepay_payments
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_ranking_alerts"
down_revision: str | None = "0016_sepay_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ranking_alert_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "notify_entered_top10", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "notify_left_top10", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "notify_improvement", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "notify_decline", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "movement_threshold", sa.Integer(), server_default="3", nullable=False
        ),
        sa.Column(
            "email_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_threshold BETWEEN 1 AND 10",
            name=op.f("ck_ranking_alert_preferences_threshold"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            name=op.f("fk_ranking_alert_preferences_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ranking_alert_preferences")),
        sa.UniqueConstraint(
            "user_id", "project_id", name="uq_ranking_alert_preferences_owner"
        ),
    )
    op.create_table(
        "ranking_alert_evaluations",
        sa.Column("check_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suppressed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("sites", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="pending", nullable=False
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed')",
            name=op.f("ck_ranking_alert_evaluations_status"),
        ),
        sa.CheckConstraint(
            "attempts BETWEEN 0 AND 5",
            name=op.f("ck_ranking_alert_evaluations_attempts"),
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["rank_checks.id"],
            name=op.f("fk_ranking_alert_evaluations_check_id_rank_checks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["keyword_id"],
            ["keywords.id"],
            name=op.f("fk_ranking_alert_evaluations_keyword_id_keywords"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_ranking_alert_evaluations_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ranking_alert_evaluations_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("check_id", name=op.f("pk_ranking_alert_evaluations")),
    )
    op.create_index(
        "ix_ranking_alert_evaluations_history",
        "ranking_alert_evaluations",
        ["keyword_id", "observed_at", "check_id"],
        unique=False,
    )
    op.create_index(
        "ix_ranking_alert_evaluations_pending",
        "ranking_alert_evaluations",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_table(
        "ranking_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_site_id", sa.Uuid(), nullable=True),
        sa.Column("site_identity", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("previous_observation_id", sa.Uuid(), nullable=False),
        sa.Column("current_observation_id", sa.Uuid(), nullable=False),
        sa.Column("previous_rank", sa.Integer(), nullable=True),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column("rank_delta", sa.Integer(), nullable=True),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("site_name", sa.String(length=200), nullable=False),
        sa.Column("device", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "alert_type IN ('entered_top10','left_top10',"
            "'rank_improved','rank_declined')",
            name=op.f("ck_ranking_alerts_type"),
        ),
        sa.CheckConstraint(
            "current_rank IS NULL OR current_rank BETWEEN 1 AND 10",
            name=op.f("ck_ranking_alerts_current_rank"),
        ),
        sa.CheckConstraint(
            "previous_rank IS NOT NULL OR current_rank IS NOT NULL",
            name=op.f("ck_ranking_alerts_rank_transition"),
        ),
        sa.CheckConstraint(
            "previous_rank IS NULL OR previous_rank BETWEEN 1 AND 10",
            name=op.f("ck_ranking_alerts_previous_rank"),
        ),
        sa.ForeignKeyConstraint(
            ["current_observation_id"],
            ["rank_checks.id"],
            name=op.f("fk_ranking_alerts_current_observation_id_rank_checks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            name=op.f("fk_ranking_alerts_keyword_id_keywords"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["previous_observation_id"],
            ["rank_checks.id"],
            name=op.f("fk_ranking_alerts_previous_observation_id_rank_checks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            name=op.f("fk_ranking_alerts_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_site_id"],
            ["tracked_sites.id"],
            name=op.f("fk_ranking_alerts_tracked_site_id_tracked_sites"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ranking_alerts")),
        sa.UniqueConstraint(
            "current_observation_id",
            "site_identity",
            "alert_type",
            name="uq_ranking_alert_event",
        ),
    )
    op.create_index(
        "ix_ranking_alerts_inbox",
        "ranking_alerts",
        ["user_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_ranking_alerts_project", "ranking_alerts", ["project_id"], unique=False
    )
    op.create_index(
        "ix_ranking_alerts_unread",
        "ranking_alerts",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_table(
        "ranking_alert_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel", sa.String(length=16), server_default="email", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=16), server_default="pending", nullable=False
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "channel = 'email'", name=op.f("ck_ranking_alert_deliveries_channel")
        ),
        sa.CheckConstraint(
            "status IN ('pending','sending','sent','suppressed','failed')",
            name=op.f("ck_ranking_alert_deliveries_status"),
        ),
        sa.CheckConstraint(
            "attempts BETWEEN 0 AND 5",
            name=op.f("ck_ranking_alert_deliveries_attempts"),
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["ranking_alerts.id"],
            name=op.f("fk_ranking_alert_deliveries_alert_id_ranking_alerts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ranking_alert_deliveries")),
        sa.UniqueConstraint("alert_id", "channel", name="uq_ranking_alert_delivery"),
    )
    op.create_index(
        "ix_ranking_alert_deliveries_pending",
        "ranking_alert_deliveries",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.add_column(
        "rank_checks", sa.Column("alert_context", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("rank_checks", "alert_context")
    op.drop_index(
        "ix_ranking_alert_deliveries_pending", table_name="ranking_alert_deliveries"
    )
    op.drop_table("ranking_alert_deliveries")
    op.drop_index(
        "ix_ranking_alerts_unread",
        table_name="ranking_alerts",
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.drop_index("ix_ranking_alerts_project", table_name="ranking_alerts")
    op.drop_index("ix_ranking_alerts_inbox", table_name="ranking_alerts")
    op.drop_table("ranking_alerts")
    op.drop_index(
        "ix_ranking_alert_evaluations_pending", table_name="ranking_alert_evaluations"
    )
    op.drop_index(
        "ix_ranking_alert_evaluations_history", table_name="ranking_alert_evaluations"
    )
    op.drop_table("ranking_alert_evaluations")
    op.drop_table("ranking_alert_preferences")
