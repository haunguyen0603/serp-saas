from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    password_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            values_callable=lambda values: [v.value for v in values],
            native_enum=False,
            create_constraint=True,
            name="user_status",
            length=16,
        ),
        default=UserStatus.ACTIVE,
        server_default="active",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
