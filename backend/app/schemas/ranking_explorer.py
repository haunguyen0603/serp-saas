from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.analytics import AnalyticsRange

ExplorerMovement = Literal[
    "improved",
    "declined",
    "unchanged",
    "entered_checked_depth",
    "left_checked_depth",
    "no_previous_data",
    "never_checked",
]
ExplorerStatus = Literal["ranked", "not_found_in_depth", "never_checked"]
ExplorerSort = Literal["keyword", "current_position", "comparison_position", "change"]
ExplorerOrder = Literal["asc", "desc"]


class ExplorerTrackedSite(BaseModel):
    id: UUID
    name: str


class ExplorerObservation(BaseModel):
    checked_at: datetime
    position: int | None
    status: Literal["ranked", "not_found_in_depth"]
    depth: int
    rank_check_id: UUID


class ExplorerMovementValue(BaseModel):
    type: ExplorerMovement
    change: int | None


class RankingExplorerItem(BaseModel):
    keyword_id: UUID
    keyword: str
    keyword_status: Literal["active", "paused"]
    tracked_site: ExplorerTrackedSite
    device: str
    comparison: ExplorerObservation | None
    current: ExplorerObservation | None
    movement: ExplorerMovementValue


class ExplorerResultsSummary(BaseModel):
    total: int
    improved: int
    declined: int
    unchanged: int
    entered_checked_depth: int
    left_checked_depth: int
    no_previous_data: int
    never_checked: int


class ExplorerPage(BaseModel):
    limit: int
    next_cursor: str | None


class RankingExplorerResponse(BaseModel):
    project_id: UUID
    device: str
    range: AnalyticsRange | Literal["custom"]
    compare_from: str | None
    compare_to: str | None
    comparison_basis: Literal[
        "range_boundary", "earliest_in_range", "custom_dates", "none"
    ]
    effective_depth: int
    supported_position_buckets: list[str]
    summary: ExplorerResultsSummary
    page: ExplorerPage
    items: list[RankingExplorerItem]
