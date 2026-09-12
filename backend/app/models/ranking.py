from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ranking(Base):
    __tablename__ = "rankings"
    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        UniqueConstraint(
            "rank_check_id", "tracked_site_id", name="uq_rankings_check_site"
        ),
        Index("ix_rankings_rank_check_id", "rank_check_id"),
        Index(
            "ix_rankings_tracked_site_id_created_at", "tracked_site_id", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rank_check_id: Mapped[UUID] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="RESTRICT"), nullable=False
    )
    tracked_site_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tracked_sites.id", ondelete="SET NULL")
    )
    tracked_domain_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tracked_domains.id", ondelete="SET NULL")
    )
    tracked_site_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    matched_domain_snapshot: Mapped[str] = mapped_column(String(253), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    result_url: Mapped[str] = mapped_column(Text, nullable=False)
    result_hostname: Mapped[str] = mapped_column(String(253), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
