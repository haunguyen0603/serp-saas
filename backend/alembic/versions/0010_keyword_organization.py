"""Project-scoped Keyword Groups and Tags.

Revision ID: 0010_keyword_organization
Revises: 0009_plan_catalog_audit
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_keyword_organization"
down_revision = "0009_plan_catalog_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keyword_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
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
            "char_length(name) BETWEEN 1 AND 80", name="ck_keyword_groups_name_length"
        ),
        sa.CheckConstraint(
            "char_length(normalized_name) BETWEEN 1 AND 80",
            name="ck_keyword_groups_normalized_name_length",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "project_id", name="uq_keyword_groups_id_project_id"),
        sa.UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_keyword_groups_project_normalized_name",
        ),
    )
    op.create_index("ix_keyword_groups_project_id", "keyword_groups", ["project_id"])
    op.create_table(
        "keyword_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("normalized_name", sa.String(length=40), nullable=False),
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
            "char_length(name) BETWEEN 1 AND 40", name="ck_keyword_tags_name_length"
        ),
        sa.CheckConstraint(
            "char_length(normalized_name) BETWEEN 1 AND 40",
            name="ck_keyword_tags_normalized_name_length",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "project_id", name="uq_keyword_tags_id_project_id"),
        sa.UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_keyword_tags_project_normalized_name",
        ),
    )
    op.create_index("ix_keyword_tags_project_id", "keyword_tags", ["project_id"])
    op.add_column("keywords", sa.Column("keyword_group_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_keywords_group_project",
        "keywords",
        "keyword_groups",
        ["keyword_group_id", "project_id"],
        ["id", "project_id"],
    )
    op.create_index(
        "ix_keywords_project_id_keyword_group_id",
        "keywords",
        ["project_id", "keyword_group_id"],
    )
    op.create_table(
        "keyword_tag_assignments",
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            ondelete="CASCADE",
            name="fk_keyword_tag_assignments_keyword_project",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id", "project_id"],
            ["keyword_tags.id", "keyword_tags.project_id"],
            ondelete="CASCADE",
            name="fk_keyword_tag_assignments_tag_project",
        ),
        sa.PrimaryKeyConstraint("keyword_id", "tag_id"),
    )
    op.create_index(
        "ix_keyword_tag_assignments_project_keyword",
        "keyword_tag_assignments",
        ["project_id", "keyword_id"],
    )
    op.create_index(
        "ix_keyword_tag_assignments_project_tag",
        "keyword_tag_assignments",
        ["project_id", "tag_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_keyword_tag_assignments_project_tag",
        table_name="keyword_tag_assignments",
    )
    op.drop_index(
        "ix_keyword_tag_assignments_project_keyword",
        table_name="keyword_tag_assignments",
    )
    op.drop_table("keyword_tag_assignments")
    op.drop_index("ix_keywords_project_id_keyword_group_id", table_name="keywords")
    op.drop_constraint("fk_keywords_group_project", "keywords", type_="foreignkey")
    op.drop_column("keywords", "keyword_group_id")
    op.drop_index("ix_keyword_tags_project_id", table_name="keyword_tags")
    op.drop_table("keyword_tags")
    op.drop_index("ix_keyword_groups_project_id", table_name="keyword_groups")
    op.drop_table("keyword_groups")
