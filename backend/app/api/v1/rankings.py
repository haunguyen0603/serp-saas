from uuid import UUID

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.dependencies.business import RankCheckQueries
from app.schemas.rank_check import LatestRankingResponse

router = APIRouter(prefix="/projects", tags=["rankings"])


@router.get(
    "/{project_id}/rankings/latest",
    response_model=LatestRankingResponse,
    responses={401: {}, 404: {}, 422: {}},
)
async def latest_rankings(
    project_id: UUID,
    current_user: CurrentUser,
    service: RankCheckQueries,
) -> LatestRankingResponse:
    return await service.latest(project_id, current_user.id)
