from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies.auth import CurrentUser
from app.dependencies.business import CompetitorAnalytics
from app.schemas.competitor_analytics import (
    CompetitorKeywordListResponse,
    CompetitorKeywordObservationResponse,
    CompetitorOverviewResponse,
    CompetitorSelectionResponse,
    CompetitorSelectionUpdate,
    CompetitorTrendsResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["competitor-analytics"])


@router.get("/competitor-sites", response_model=CompetitorSelectionResponse)
async def get_competitor_sites(
    project_id: UUID,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
) -> CompetitorSelectionResponse:
    return await service.get_selection(project_id, current_user.id)


@router.put("/competitor-sites", response_model=CompetitorSelectionResponse)
async def replace_competitor_sites(
    project_id: UUID,
    data: CompetitorSelectionUpdate,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
) -> CompetitorSelectionResponse:
    return await service.replace_selection(project_id, current_user.id, data)


@router.get("/competitors/overview", response_model=CompetitorOverviewResponse)
async def competitor_overview(
    project_id: UUID,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
    range: str = "30d",
    start_date: str | None = None,
    end_date: str | None = None,
    group_id: str | None = None,
    tag_ids: str | None = None,
    tag_match: str = "any",
) -> CompetitorOverviewResponse:
    return await service.overview(
        project_id,
        current_user.id,
        range_value=range,
        start_date=start_date,
        end_date=end_date,
        group_id=group_id,
        tag_ids=tag_ids,
        tag_match=tag_match,
    )


@router.get("/competitors/keywords", response_model=CompetitorKeywordListResponse)
async def competitor_keywords(
    project_id: UUID,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
    q: Annotated[str | None, Query(max_length=512)] = None,
    range: str = "30d",
    start_date: str | None = None,
    end_date: str | None = None,
    group_id: str | None = None,
    tag_ids: str | None = None,
    tag_match: str = "any",
    comparison_state: str = "all",
    opportunity: bool = False,
    opponent_site_id: UUID | None = None,
    sort: str = "keyword",
    order: str = "asc",
    limit: int = 50,
    cursor: str | None = None,
) -> CompetitorKeywordListResponse:
    return await service.keywords_page(
        project_id,
        current_user.id,
        range_value=range,
        start_date=start_date,
        end_date=end_date,
        q=q,
        group_id=group_id,
        tag_ids=tag_ids,
        tag_match=tag_match,
        comparison_state=comparison_state,
        opportunity=opportunity,
        opponent_site_id=opponent_site_id,
        sort=sort,
        order=order,
        limit=limit,
        cursor=cursor,
    )


@router.get("/competitors/trends", response_model=CompetitorTrendsResponse)
async def competitor_trends(
    project_id: UUID,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
    range: str = "30d",
    start_date: str | None = None,
    end_date: str | None = None,
    group_id: str | None = None,
    tag_ids: str | None = None,
    tag_match: str = "any",
) -> CompetitorTrendsResponse:
    return await service.trends(
        project_id,
        current_user.id,
        range_value=range,
        start_date=start_date,
        end_date=end_date,
        group_id=group_id,
        tag_ids=tag_ids,
        tag_match=tag_match,
    )


@router.get(
    "/competitors/keywords/{keyword_id}/observations",
    response_model=CompetitorKeywordObservationResponse,
)
async def competitor_keyword_observation(
    project_id: UUID,
    keyword_id: UUID,
    current_user: CurrentUser,
    service: CompetitorAnalytics,
    range: str = "30d",
    start_date: str | None = None,
    end_date: str | None = None,
) -> CompetitorKeywordObservationResponse:
    return await service.keyword_observation(
        project_id,
        keyword_id,
        current_user.id,
        range_value=range,
        start_date=start_date,
        end_date=end_date,
    )
