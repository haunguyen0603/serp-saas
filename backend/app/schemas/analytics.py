from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

AnalyticsRange = Literal["7d", "30d", "90d"]
MovementBasis = Literal["range_boundary", "earliest_in_range", "none"]


class RankingDistributionResponse(BaseModel):
    effective_depth: int
    buckets: dict[str, int]


class ProjectAnalyticsSummaryResponse(BaseModel):
    project_id: UUID
    device: str
    range: AnalyticsRange
    as_of: datetime
    comparison_basis: MovementBasis
    total_keywords: int
    observed_keywords: int
    never_checked: int
    ranked_keywords: int
    not_found_in_depth: int
    top_3: int
    top_10: int
    improved: int
    declined: int
    unchanged: int
    newly_ranked: int
    lost_ranking: int
    entered_checked_depth: int
    left_checked_depth: int
    no_previous_data: int
    distribution: RankingDistributionResponse


class RankingMover(BaseModel):
    keyword_id: UUID
    keyword: str
    tracked_site_id: UUID
    tracked_site_name: str
    previous_position: int
    current_position: int
    change: int


class RankingMoversResponse(BaseModel):
    winners: list[RankingMover]
    losers: list[RankingMover]


class HistoryTrackedSite(BaseModel):
    id: UUID
    name: str


class RankingHistoryPoint(BaseModel):
    checked_at: datetime
    position: int | None
    status: Literal["ranked", "not_found_in_depth"]
    checked_depth: int
    rank_check_id: UUID


class KeywordRankingHistoryResponse(BaseModel):
    keyword_id: UUID
    keyword: str
    tracked_site: HistoryTrackedSite
    device: str
    range: AnalyticsRange
    points: list[RankingHistoryPoint]
