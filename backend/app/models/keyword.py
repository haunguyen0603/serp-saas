from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        CheckConstraint(
            "char_length(keyword) BETWEEN 1 AND 512", name="keyword_length"
        ),
        CheckConstraint(
            "char_length(keyword_normalized) BETWEEN 1 AND 512",
            name="keyword_normalized_length",
        ),
        UniqueConstraint(
            "project_id",
            "keyword_normalized",
            name="uq_keywords_project_keyword_normalized",
        ),
        UniqueConstraint("id", "project_id", name="uq_keywords_id_project_id"),
        Index("ix_keywords_project_id", "project_id"),
        Index("ix_keywords_project_id_active", "project_id", "active"),
        Index("ix_keywords_project_id_created_at", "project_id", "created_at"),
        Index(
            "ix_keywords_project_id_keyword_normalized",
            "project_id",
            "keyword_normalized",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
