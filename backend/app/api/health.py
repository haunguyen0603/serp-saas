from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import ErrorResponse, HealthResponse
from app.services.health import check_database, check_redis

router = APIRouter(prefix="/health", tags=["health"])


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


@router.get("")
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/db", responses={503: {"model": ErrorResponse}})
async def database_health(
    session: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> HealthResponse:
    await check_database(session)
    return HealthResponse()


@router.get("/redis", responses={503: {"model": ErrorResponse}})
async def redis_health(client: Annotated[Redis, Depends(get_redis)]) -> HealthResponse:
    await check_redis(client)
    return HealthResponse()
