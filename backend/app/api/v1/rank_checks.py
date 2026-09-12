from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies.auth import CurrentUser
from app.dependencies.business import RankCheckQueries
from app.schemas.rank_check import (
    RankCheckDetailResponse,
    RankCheckListResponse,
    RankCheckStatusFilter,
)

router = APIRouter(prefix="/projects", tags=["rank-checks"])


@router.get(
    "/{project_id}/keywords/{keyword_id}/rank-checks",
    response_model=RankCheckListResponse,
    responses={401: {}, 404: {}, 422: {}},
)
async def rank_check_history(
    project_id: UUID,
    keyword_id: UUID,
    current_user: CurrentUser,
    service: RankCheckQueries,
    status: RankCheckStatusFilter = "all",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> RankCheckListResponse:
    return await service.history(
        project_id,
        keyword_id,
        current_user.id,
        status=status,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}",
    response_model=RankCheckDetailResponse,
    responses={401: {}, 404: {}, 422: {}},
)
async def rank_check_detail(
    project_id: UUID,
    keyword_id: UUID,
    check_id: UUID,
    current_user: CurrentUser,
    service: RankCheckQueries,
) -> RankCheckDetailResponse:
    return await service.detail(project_id, keyword_id, check_id, current_user.id)
