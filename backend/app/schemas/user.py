from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.user import User, UserStatus


class UserResponse(BaseModel):
    id: UUID
    is_platform_admin: bool = False
    email: str
    status: UserStatus
    email_verified: bool
    terms_accepted_at: datetime
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            is_platform_admin=user.is_platform_admin,
            email=user.email,
            status=user.status,
            email_verified=user.email_verified_at is not None,
            terms_accepted_at=user.terms_accepted_at,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
