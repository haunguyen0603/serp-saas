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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 200", name="name_length"
        ),
        CheckConstraint("search_engine = 'google'", name="search_engine"),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        CheckConstraint(
            "language_code ~ '^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$'",
            name="language_code_format",
        ),
        CheckConstraint("device IN ('desktop', 'mobile')", name="device_value"),
        Index("ix_projects_user_id", "user_id"),
        Index("ix_projects_user_id_status", "user_id", "status"),
        Index("ix_projects_user_id_created_at", "user_id", "created_at"),
        UniqueConstraint("id", "user_id", name="uq_projects_id_user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    search_engine: Mapped[str] = mapped_column(
        String(32), nullable=False, default="google", server_default="google"
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    language_code: Mapped[str] = mapped_column(String(16), nullable=False)
    device: Mapped[str] = mapped_column(
        String(16), nullable=False, default="desktop", server_default="desktop"
    )
    location: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="project_status",
            length=16,
        ),
        nullable=False,
        default=ProjectStatus.ACTIVE,
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
