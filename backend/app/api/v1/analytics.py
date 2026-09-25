from uuid import UUID

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.dependencies.business import ProjectAnalytics
from app.schemas.analytics import (
    KeywordRankingHistoryResponse,
    ProjectAnalyticsSummaryResponse,
    RankingDistributionResponse,
    RankingMoversResponse,
)

router = APIRouter(prefix="/projects", tags=["analytics"])


@router.get(
    "/{project_id}/analytics/summary",
    response_model=ProjectAnalyticsSummaryResponse,
)
async def analytics_summary(
    project_id: UUID,
    current_user: CurrentUser,
    service: ProjectAnalytics,
    device: str | None = None,
    range: str = "30d",
) -> ProjectAnalyticsSummaryResponse:
    return await service.get_summary(
        project_id, current_user.id, device=device, range_value=range
    )


@router.get(
    "/{project_id}/analytics/organization-summary",
    response_model=ProjectAnalyticsSummaryResponse,
)
async def organization_analytics_summary(
    project_id: UUID,
    current_user: CurrentUser,
    service: ProjectAnalytics,
    group_id: UUID | None = None,
    tag_id: UUID | None = None,
    device: str | None = None,
    range: str = "30d",
) -> ProjectAnalyticsSummaryResponse:
    return await service.get_organization_summary(
        project_id,
        current_user.id,
        device=device,
        range_value=range,
        group_id=group_id,
        tag_id=tag_id,
    )


@router.get(
    "/{project_id}/analytics/distribution",
    response_model=RankingDistributionResponse,
)
async def analytics_distribution(
    project_id: UUID,
    current_user: CurrentUser,
    service: ProjectAnalytics,
    device: str | None = None,
    range: str = "30d",
) -> RankingDistributionResponse:
    return await service.get_distribution(
        project_id, current_user.id, device=device, range_value=range
    )


@router.get("/{project_id}/analytics/movers", response_model=RankingMoversResponse)
async def analytics_movers(
    project_id: UUID,
    current_user: CurrentUser,
    service: ProjectAnalytics,
    device: str | None = None,
    range: str = "30d",
    limit: int = 10,
) -> RankingMoversResponse:
    return await service.get_movers(
        project_id,
        current_user.id,
        device=device,
        range_value=range,
        limit=limit,
    )


@router.get(
    "/{project_id}/keywords/{keyword_id}/ranking-history",
    response_model=KeywordRankingHistoryResponse,
)
async def keyword_ranking_history(
    project_id: UUID,
    keyword_id: UUID,
    tracked_site_id: UUID,
    current_user: CurrentUser,
    service: ProjectAnalytics,
    device: str | None = None,
    range: str = "30d",
) -> KeywordRankingHistoryResponse:
    return await service.get_keyword_history(
        project_id,
        keyword_id,
        current_user.id,
        tracked_site_id=tracked_site_id,
        device=device,
        range_value=range,
    )
