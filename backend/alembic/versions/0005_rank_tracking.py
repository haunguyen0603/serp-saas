"""Provider-independent rank checks, organic snapshots, and rankings."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_rank_tracking"
down_revision: str | None = "0004_project_refactor_sites"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_projects_id_user_id", "projects", ["id", "user_id"])
    op.create_unique_constraint(
        "uq_keywords_id_project_id", "keywords", ["id", "project_id"]
    )

    op.create_table(
        "rank_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "succeeded",
                "failed",
                name="rank_check_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("query_snapshot", sa.Text(), nullable=False),
        sa.Column("search_engine_snapshot", sa.String(32), nullable=False),
        sa.Column("country_code_snapshot", sa.String(2), nullable=False),
        sa.Column("language_code_snapshot", sa.String(16), nullable=False),
        sa.Column("device_snapshot", sa.String(16), nullable=False),
        sa.Column("location_snapshot", sa.Text()),
        sa.Column("result_limit", sa.Integer(), nullable=False),
        sa.Column(
            "provider_request_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("provider_request_id", sa.String(255)),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result_limit BETWEEN 1 AND 100",
            name="ck_rank_checks_result_limit",
        ),
        sa.CheckConstraint(
            "provider_request_count >= 0",
            name="ck_rank_checks_provider_request_count",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            name="fk_rank_checks_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            name="fk_rank_checks_keyword_id_keywords",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rank_checks_keyword_id_created_at",
        "rank_checks",
        ["keyword_id", "created_at"],
    )
    op.create_index(
        "ix_rank_checks_project_id_created_at",
        "rank_checks",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_rank_checks_user_id_created_at",
        "rank_checks",
        ["user_id", "created_at"],
    )
    op.create_index("ix_rank_checks_status", "rank_checks", ["status"])
    op.create_index(
        "uq_rank_checks_keyword_running",
        "rank_checks",
        ["keyword_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )

    op.create_table(
        "rank_check_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rank_check_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("hostname", sa.String(253), nullable=False),
        sa.Column("displayed_url", sa.Text()),
        sa.Column("snippet", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 1", name="ck_rank_check_results_position_positive"
        ),
        sa.ForeignKeyConstraint(
            ["rank_check_id"],
            ["rank_checks.id"],
            name="fk_rank_check_results_rank_check_id_rank_checks",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rank_check_id",
            "position",
            name="uq_rank_check_results_check_position",
        ),
    )
    op.create_index(
        "ix_rank_check_results_rank_check_id_position",
        "rank_check_results",
        ["rank_check_id", "position"],
    )

    op.create_table(
        "rankings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rank_check_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_site_id", sa.Uuid()),
        sa.Column("tracked_domain_id", sa.Uuid()),
        sa.Column("tracked_site_name_snapshot", sa.String(200), nullable=False),
        sa.Column("matched_domain_snapshot", sa.String(253), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("result_url", sa.Text(), nullable=False),
        sa.Column("result_hostname", sa.String(253), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("position >= 1", name="ck_rankings_position_positive"),
        sa.ForeignKeyConstraint(
            ["rank_check_id"],
            ["rank_checks.id"],
            name="fk_rankings_rank_check_id_rank_checks",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_site_id"],
            ["tracked_sites.id"],
            name="fk_rankings_tracked_site_id_tracked_sites",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_domain_id"],
            ["tracked_domains.id"],
            name="fk_rankings_tracked_domain_id_tracked_domains",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rank_check_id", "tracked_site_id", name="uq_rankings_check_site"
        ),
    )
    op.create_index("ix_rankings_rank_check_id", "rankings", ["rank_check_id"])
    op.create_index(
        "ix_rankings_tracked_site_id_created_at",
        "rankings",
        ["tracked_site_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rankings_tracked_site_id_created_at", table_name="rankings")
    op.drop_index("ix_rankings_rank_check_id", table_name="rankings")
    op.drop_table("rankings")
    op.drop_index(
        "ix_rank_check_results_rank_check_id_position",
        table_name="rank_check_results",
    )
    op.drop_table("rank_check_results")
    op.drop_index("uq_rank_checks_keyword_running", table_name="rank_checks")
    op.drop_index("ix_rank_checks_status", table_name="rank_checks")
    op.drop_index("ix_rank_checks_user_id_created_at", table_name="rank_checks")
    op.drop_index("ix_rank_checks_project_id_created_at", table_name="rank_checks")
    op.drop_index("ix_rank_checks_keyword_id_created_at", table_name="rank_checks")
    op.drop_table("rank_checks")
    op.drop_constraint("uq_keywords_id_project_id", "keywords", type_="unique")
    op.drop_constraint("uq_projects_id_user_id", "projects", type_="unique")
