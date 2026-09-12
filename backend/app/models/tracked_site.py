from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrackedSiteStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class TrackedSite(Base):
    __tablename__ = "tracked_sites"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 200", name="name_length"
        ),
        UniqueConstraint("id", "user_id", name="uq_tracked_sites_id_user_id"),
        Index("ix_tracked_sites_user_id", "user_id"),
        Index("ix_tracked_sites_user_id_status", "user_id", "status"),
        Index("ix_tracked_sites_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[TrackedSiteStatus] = mapped_column(
        Enum(
            TrackedSiteStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="tracked_site_status",
            length=16,
        ),
        nullable=False,
        default=TrackedSiteStatus.ACTIVE,
        server_default="active",
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
