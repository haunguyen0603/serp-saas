from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CompetitorStatus = Literal[
    "ranked",
    "not_found_in_checked_depth",
    "not_observed",
    "ambiguous_match",
]
CoverageQuality = Literal["complete", "partial", "insufficient_data"]


class CompetitorSelectionUpdate(BaseModel):
    primary_tracked_site_id: UUID
    competitor_tracked_site_ids: list[UUID] = Field(max_length=5)

    @model_validator(mode="after")
    def validate_unique_sites(self) -> "CompetitorSelectionUpdate":
        competitors = self.competitor_tracked_site_ids
        if len(competitors) != len(set(competitors)):
            raise ValueError("Competitor sites must be unique.")
        if self.primary_tracked_site_id in competitors:
            raise ValueError("The primary site cannot also be a competitor.")
        return self


class CompetitorSelectedSite(BaseModel):
    tracked_site_id: UUID
    name: str
    primary_domain: str | None
    role: Literal["primary", "competitor"]


class CompetitorSelectionResponse(BaseModel):
    project_id: UUID
    primary_site: CompetitorSelectedSite | None
    competitor_sites: list[CompetitorSelectedSite]
    max_competitors: int = 5
    selection_basis: Literal["current_selection"] = "current_selection"
    historical_alias_semantics: Literal["current_active_aliases"] = (
        "current_active_aliases"
    )


class CompetitorSiteMetric(BaseModel):
    tracked_site_id: UUID
    name: str
    top_3: int
    top_n: int
    comparable_keywords: int
    observed_top_n_coverage_pct: float
    not_found_in_checked_depth: int
    not_observed: int
    ambiguous_match: int


class HeadToHeadMetric(BaseModel):
    opponent_site_id: UUID
    opponent_name: str
    both_numeric_ranked: int
    primary_ahead: int
    tied: int
    competitor_ahead: int
    excluded_unpaired: int
    opportunities: int


class CompetitorOverviewResponse(BaseModel):
    project_id: UUID
    device: str
    range: Literal["7d", "30d", "90d", "custom"]
    as_of: datetime
    effective_depth: int
    top_n: int
    keyword_cohort: int
    qualifying_keywords: int
    partial_or_unobserved_keywords: int
    primary_site: CompetitorSelectedSite
    sites: list[CompetitorSiteMetric]
    comparisons: list[HeadToHeadMetric]
    coverage_quality: CoverageQuality
    latest_successful_check_at: datetime | None
    selection_basis: Literal["current_selection"] = "current_selection"
    historical_alias_semantics: Literal["current_active_aliases"] = (
        "current_active_aliases"
    )


class CompetitorSiteObservation(BaseModel):
    tracked_site_id: UUID
    name: str
    status: CompetitorStatus
    position: int | None
    checked_depth: int
    matched_url: str | None
    matched_hostname: str | None


class CompetitorKeywordRow(BaseModel):
    keyword_id: UUID
    keyword: str
    checked_at: datetime
    rank_check_id: UUID
    checked_depth: int
    snapshot_complete: bool
    sites: list[CompetitorSiteObservation]
    opponent_site_id: UUID | None
    position_gap: int | None
    comparison_state: Literal[
        "both_ranked",
        "my_site_ahead",
        "competitor_ahead",
        "tied",
        "not_comparable",
    ]
    opportunity: bool


class CompetitorKeywordListResponse(BaseModel):
    project_id: UUID
    items: list[CompetitorKeywordRow]
    next_cursor: str | None
    has_more: bool
    total: int
    top_n: int
    opponent_site_id: UUID | None


class CompetitorTrendSitePoint(BaseModel):
    tracked_site_id: UUID
    name: str
    top_n_appearances: int
    comparable_keywords: int
    observed_top_n_coverage_pct: float
    not_observed: int


class CompetitorTrendPoint(BaseModel):
    date: date
    observed_keywords: int
    coverage_quality: CoverageQuality
    sites: list[CompetitorTrendSitePoint]


class CompetitorTrendsResponse(BaseModel):
    project_id: UUID
    range: Literal["7d", "30d", "90d", "custom"]
    top_n: int
    points: list[CompetitorTrendPoint]
    gaps_are_not_interpolated: bool = True


class CompetitorMatchedResult(BaseModel):
    position: int
    url: str
    hostname: str
    title: str | None


class CompetitorObservationSiteDetail(CompetitorSiteObservation):
    matched_results: list[CompetitorMatchedResult]


class CompetitorKeywordObservationResponse(BaseModel):
    project_id: UUID
    keyword_id: UUID
    keyword: str
    rank_check_id: UUID
    checked_at: datetime
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None
    checked_depth: int
    snapshot_complete: bool
    coverage_quality: CoverageQuality
    sites: list[CompetitorObservationSiteDetail]
