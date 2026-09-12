import asyncio
import logging
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DependencyUnavailable
from app.db.health import ping_database

logger = logging.getLogger(__name__)


async def check_database(session: AsyncSession) -> None:
    try:
        async with asyncio.timeout(5):
            if not await ping_database(session):
                raise DependencyUnavailable("database")
    except Exception:
        logger.warning("Database health check failed")
        raise DependencyUnavailable("database") from None


async def check_redis(client: Redis) -> None:
    try:
        async with asyncio.timeout(5):
            if not await cast(Awaitable[bool], client.ping()):
                raise DependencyUnavailable("redis")
    except Exception:
        logger.warning("Redis health check failed")
        raise DependencyUnavailable("redis") from None
