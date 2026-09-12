from uuid import UUID

from app.core.errors import AppError
from app.models.user import User, UserStatus
from app.repositories.user import UserRepository


def require_active(user: User) -> User:
    if user.status != UserStatus.ACTIVE:
        raise AppError(403, "DISABLED_USER", "This account is disabled.")
    return user


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def current_user(self, user_id: UUID) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise AppError(401, "INVALID_ACCESS_TOKEN", "Invalid access token.")
        return require_active(user)
