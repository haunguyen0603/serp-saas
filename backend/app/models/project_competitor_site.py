from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectSiteRole(StrEnum):
    PRIMARY = "primary"
    COMPETITOR = "competitor"


class ProjectCompetitorSite(Base):
    """A durable, user-selected comparison lens for one Project."""

    __tablename__ = "project_competitor_sites"
    __table_args__ = (
        CheckConstraint("role IN ('primary','competitor')", name="role_valid"),
        CheckConstraint("display_order BETWEEN 0 AND 5", name="display_order_valid"),
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tracked_site_id", "user_id"],
            ["tracked_sites.id", "tracked_sites.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "id", "project_id", name="uq_project_competitor_sites_id_project"
        ),
        Index(
            "uq_project_competitor_sites_active_site",
            "project_id",
            "tracked_site_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        Index(
            "uq_project_competitor_sites_active_primary",
            "project_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL AND role = 'primary'"),
        ),
        Index(
            "ix_project_competitor_sites_active_project",
            "project_id",
            "role",
            postgresql_where=text("archived_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    tracked_site_id: Mapped[UUID] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
