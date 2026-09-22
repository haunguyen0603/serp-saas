from uuid import UUID

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.dependencies.business import RankingExplorer
from app.schemas.ranking_explorer import RankingExplorerResponse

router = APIRouter(prefix="/projects", tags=["ranking-explorer"])


@router.get("/{project_id}/ranking-explorer", response_model=RankingExplorerResponse)
async def ranking_explorer(
    project_id: UUID,
    current_user: CurrentUser,
    service: RankingExplorer,
    q: str | None = None,
    range: str = "30d",
    compare_from: str | None = None,
    compare_to: str | None = None,
    movement: str | None = None,
    position_bucket: str | None = None,
    tracked_site_id: UUID | None = None,
    status: str | None = None,
    sort: str = "keyword",
    order: str = "asc",
    limit: int = 50,
    cursor: str | None = None,
) -> RankingExplorerResponse:
    return await service.list(
        project_id,
        current_user.id,
        q=q,
        range_value=range,
        compare_from=compare_from,
        compare_to=compare_to,
        movement=movement,
        position_bucket=position_bucket,
        tracked_site_id=tracked_site_id,
        status=status,
        sort=sort,
        order=order,
        limit=limit,
        cursor=cursor,
    )
