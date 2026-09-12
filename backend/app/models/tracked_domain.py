from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrackedDomain(Base):
    __tablename__ = "tracked_domains"
    __table_args__ = (
        CheckConstraint("char_length(domain) BETWEEN 1 AND 253", name="domain_length"),
        CheckConstraint(
            "NOT is_primary OR active", name="primary_domain_must_be_active"
        ),
        ForeignKeyConstraint(
            ["tracked_site_id", "user_id"],
            ["tracked_sites.id", "tracked_sites.user_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("user_id", "domain", name="uq_tracked_domains_user_domain"),
        Index("ix_tracked_domains_user_id", "user_id"),
        Index("ix_tracked_domains_tracked_site_id", "tracked_site_id"),
        Index("ix_tracked_domains_tracked_site_id_active", "tracked_site_id", "active"),
        Index(
            "uq_tracked_domains_one_primary",
            "tracked_site_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    tracked_site_id: Mapped[UUID] = mapped_column(nullable=False)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
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
