"""Project competitor selections for persisted SERP analytics.

Revision ID: 0012_competitor_analytics
Revises: 0011_reports
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_competitor_analytics"
down_revision: str | None = "0011_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_competitor_sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_site_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "role IN ('primary','competitor')",
            name="ck_project_competitor_sites_role_valid",
        ),
        sa.CheckConstraint(
            "display_order BETWEEN 0 AND 5",
            name="ck_project_competitor_sites_display_order_valid",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_site_id", "user_id"],
            ["tracked_sites.id", "tracked_sites.user_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "project_id", name="uq_project_competitor_sites_id_project"
        ),
    )
    op.create_index(
        "uq_project_competitor_sites_active_site",
        "project_competitor_sites",
        ["project_id", "tracked_site_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_index(
        "uq_project_competitor_sites_active_primary",
        "project_competitor_sites",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL AND role = 'primary'"),
    )
    op.create_index(
        "ix_project_competitor_sites_active_project",
        "project_competitor_sites",
        ["project_id", "role"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    # Supports range-scoped latest-check selection without altering old rows.
    op.create_index(
        "ix_rank_checks_competitor_window",
        "rank_checks",
        ["project_id", "user_id", "status", "keyword_id", "completed_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rank_checks_competitor_window", table_name="rank_checks")
    op.drop_index(
        "ix_project_competitor_sites_active_project",
        table_name="project_competitor_sites",
    )
    op.drop_index(
        "uq_project_competitor_sites_active_primary",
        table_name="project_competitor_sites",
    )
    op.drop_index(
        "uq_project_competitor_sites_active_site",
        table_name="project_competitor_sites",
    )
    op.drop_table("project_competitor_sites")
