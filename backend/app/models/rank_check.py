from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RankCheckStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RankCheck(Base):
    __tablename__ = "rank_checks"
    __table_args__ = (
        CheckConstraint("result_limit BETWEEN 1 AND 100", name="result_limit"),
        CheckConstraint("provider_request_count >= 0", name="provider_request_count"),
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["projects.id", "projects.user_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["keyword_id", "project_id"],
            ["keywords.id", "keywords.project_id"],
            ondelete="RESTRICT",
        ),
        Index("ix_rank_checks_keyword_id_created_at", "keyword_id", "created_at"),
        Index("ix_rank_checks_project_id_created_at", "project_id", "created_at"),
        Index("ix_rank_checks_user_id_created_at", "user_id", "created_at"),
        Index("ix_rank_checks_status", "status"),
        Index(
            "uq_rank_checks_keyword_running",
            "keyword_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    keyword_id: Mapped[UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[RankCheckStatus] = mapped_column(
        Enum(
            RankCheckStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="rank_check_status",
            length=16,
        ),
        nullable=False,
    )
    query_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    search_engine_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    country_code_snapshot: Mapped[str] = mapped_column(String(2), nullable=False)
    language_code_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    device_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    location_snapshot: Mapped[str | None] = mapped_column(Text)
    result_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_request_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    provider_request_id: Mapped[str | None] = mapped_column(String(255))
    provider_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
