from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping_database(session: AsyncSession) -> bool:
    return bool(await session.scalar(text("SELECT 1")) == 1)
