from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RankCheckProviderAttempt(Base):
    __tablename__ = "rank_check_provider_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number >= 1", name="attempt_number_positive"),
        CheckConstraint("provider_request_count >= 1", name="request_count_positive"),
        UniqueConstraint(
            "rank_check_id", "attempt_number", name="uq_provider_attempt_check_number"
        ),
        Index("ix_provider_attempt_check_number", "rank_check_id", "attempt_number"),
        Index("ix_provider_attempt_provider_created_at", "provider", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rank_check_id: Mapped[UUID] = mapped_column(
        ForeignKey("rank_checks.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ProviderAttemptStatus] = mapped_column(
        Enum(
            ProviderAttemptStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="provider_attempt_status",
            length=16,
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    provider_request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
