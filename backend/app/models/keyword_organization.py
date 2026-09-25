from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KeywordGroup(Base):
    __tablename__ = "keyword_groups"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint(
            "char_length(normalized_name) BETWEEN 1 AND 80",
            name="normalized_name_length",
        ),
        UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_keyword_groups_project_normalized_name",
        ),
        UniqueConstraint("id", "project_id", name="uq_keyword_groups_id_project_id"),
        Index("ix_keyword_groups_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class KeywordTag(Base):
    __tablename__ = "keyword_tags"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 40", name="name_length"),
        CheckConstraint(
            "char_length(normalized_name) BETWEEN 1 AND 40",
            name="normalized_name_length",
        ),
        UniqueConstraint(
            "project_id",
            "normalized_name",
            name="uq_keyword_tags_project_normalized_name",
        ),
        UniqueConstraint("id", "project_id", name="uq_keyword_tags_id_project_id"),
        Index("ix_keyword_tags_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    keywords = relationship(
        "Keyword",
        secondary="keyword_tag_assignments",
        viewonly=True,
        lazy="raise",
        order_by="(Keyword.keyword_normalized, Keyword.id)",
    )


class KeywordTagAssignment(Base):
    __tablename__ = "keyword_tag_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            ondelete="CASCADE",
            name="fk_keyword_tag_assignments_keyword_project",
        ),
        ForeignKeyConstraint(
            ["tag_id", "project_id"],
            ["keyword_tags.id", "keyword_tags.project_id"],
            ondelete="CASCADE",
            name="fk_keyword_tag_assignments_tag_project",
        ),
        Index(
            "ix_keyword_tag_assignments_project_tag",
            "project_id",
            "tag_id",
        ),
        Index(
            "ix_keyword_tag_assignments_project_keyword",
            "project_id",
            "keyword_id",
        ),
    )

    keyword_id: Mapped[UUID] = mapped_column(primary_key=True)
    tag_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
