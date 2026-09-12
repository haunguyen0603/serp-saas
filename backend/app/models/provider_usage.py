from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    __table_args__ = (
        CheckConstraint("request_count >= 0", name="request_count"),
        CheckConstraint("success_count >= 0", name="success_count"),
        CheckConstraint("failure_count >= 0", name="failure_count"),
        CheckConstraint("fallback_count >= 0", name="fallback_count"),
        UniqueConstraint(
            "provider", "period_type", "period_key", name="uq_provider_usage_period"
        ),
        Index("ix_provider_usage_provider_period_key", "provider", "period_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="monthly", server_default="monthly"
    )
    period_key: Mapped[str] = mapped_column(String(7), nullable=False)
    request_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    fallback_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
