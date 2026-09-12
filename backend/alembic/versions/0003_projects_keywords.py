"""User-owned projects and project-owned keyword configurations."""

import sqlalchemy as sa

from alembic import op

revision: str = "0003_projects_keywords"
down_revision: str | None = "0002_authentication"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column(
            "default_search_engine",
            sa.String(32),
            server_default="google",
            nullable=False,
        ),
        sa.Column("default_country_code", sa.String(2), nullable=False),
        sa.Column("default_language_code", sa.String(16), nullable=False),
        sa.Column(
            "default_device", sa.String(16), server_default="desktop", nullable=False
        ),
        sa.Column("default_location", sa.Text()),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="project_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default="active",
            nullable=False,
        ),
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
            "char_length(btrim(name)) BETWEEN 1 AND 200", name="ck_projects_name_length"
        ),
        sa.CheckConstraint(
            "char_length(domain) BETWEEN 1 AND 253", name="ck_projects_domain_length"
        ),
        sa.CheckConstraint(
            "default_search_engine = 'google'", name="ck_projects_search_engine"
        ),
        sa.CheckConstraint(
            "default_country_code ~ '^[A-Z]{2}$'",
            name="ck_projects_country_code_format",
        ),
        sa.CheckConstraint(
            "default_language_code ~ '^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$'",
            name="ck_projects_language_code_format",
        ),
        sa.CheckConstraint(
            "default_device IN ('desktop', 'mobile')", name="ck_projects_device_value"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_index("ix_projects_user_id_status", "projects", ["user_id", "status"])
    op.create_index(
        "ix_projects_user_id_created_at", "projects", ["user_id", "created_at"]
    )

    op.create_table(
        "keywords",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("keyword_normalized", sa.Text(), nullable=False),
        sa.Column("search_engine", sa.String(32), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("language_code", sa.String(16), nullable=False),
        sa.Column("device", sa.String(16), nullable=False),
        sa.Column("location", sa.Text()),
        sa.Column("location_normalized", sa.Text(), server_default="", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
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
            "char_length(keyword) BETWEEN 1 AND 512", name="ck_keywords_keyword_length"
        ),
        sa.CheckConstraint(
            "char_length(keyword_normalized) BETWEEN 1 AND 512",
            name="ck_keywords_keyword_normalized_length",
        ),
        sa.CheckConstraint(
            "search_engine = 'google'", name="ck_keywords_search_engine"
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'", name="ck_keywords_country_code_format"
        ),
        sa.CheckConstraint(
            "language_code ~ '^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$'",
            name="ck_keywords_language_code_format",
        ),
        sa.CheckConstraint(
            "device IN ('desktop', 'mobile')", name="ck_keywords_device_value"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "keyword_normalized",
            "search_engine",
            "country_code",
            "language_code",
            "device",
            "location_normalized",
            name="uq_keywords_tracking_configuration",
        ),
    )
    op.create_index("ix_keywords_project_id", "keywords", ["project_id"])
    op.create_index(
        "ix_keywords_project_id_active", "keywords", ["project_id", "active"]
    )
    op.create_index(
        "ix_keywords_project_id_created_at", "keywords", ["project_id", "created_at"]
    )
    op.create_index(
        "ix_keywords_project_id_keyword_normalized",
        "keywords",
        ["project_id", "keyword_normalized"],
    )


def downgrade() -> None:
    op.drop_index("ix_keywords_project_id_keyword_normalized", table_name="keywords")
    op.drop_index("ix_keywords_project_id_created_at", table_name="keywords")
    op.drop_index("ix_keywords_project_id_active", table_name="keywords")
    op.drop_index("ix_keywords_project_id", table_name="keywords")
    op.drop_table("keywords")
    op.drop_index("ix_projects_user_id_created_at", table_name="projects")
    op.drop_index("ix_projects_user_id_status", table_name="projects")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")
