from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, email: str, password_hash: str, terms_accepted_at: datetime
    ) -> User | None:
        # A database-level conflict target handles concurrent signups safely.
        statement = (
            insert(User)
            .values(
                email=normalize_email(email),
                password_hash=password_hash,
                terms_accepted_at=terms_accepted_at,
            )
            .on_conflict_do_nothing(index_elements=[User.email])
            .returning(User)
        )
        return cast(User | None, await self.session.scalar(statement))

    async def get_by_email(
        self, email: str, *, for_update: bool = False
    ) -> User | None:
        statement = select(User).where(User.email == normalize_email(email))
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            User | None,
            await self.session.scalar(statement),
        )

    async def get_by_id(
        self, user_id: UUID, *, for_update: bool = False
    ) -> User | None:
        if for_update:
            return cast(
                User | None,
                await self.session.scalar(
                    select(User)
                    .where(User.id == user_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                ),
            )
        return await self.session.get(User, user_id)

    async def record_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()
