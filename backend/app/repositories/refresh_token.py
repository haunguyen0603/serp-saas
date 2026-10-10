from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        return cast(
            RefreshToken | None,
            await self.session.scalar(
                select(RefreshToken)
                .where(RefreshToken.token_hash == token_hash)
                .with_for_update()
                .execution_options(populate_existing=True)
            ),
        )

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return cast(
            RefreshToken | None,
            await self.session.scalar(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            ),
        )

    async def revoke(
        self, token: RefreshToken, now: datetime, *, used: bool = False
    ) -> None:
        token.revoked_at = token.revoked_at or now
        if used:
            token.last_used_at = now
        await self.session.flush()
