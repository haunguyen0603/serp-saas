from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_provider_attempt import RankCheckProviderAttempt
from app.models.rank_check_result import RankCheckResult
from app.models.ranking import Ranking


class RankCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class ProjectRankCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keyword_ids: list[UUID] | None = Field(default=None, max_length=100)


class OrganicResultResponse(BaseModel):
    position: int
    title: str | None
    url: str
    hostname: str
    displayed_url: str | None
    snippet: str | None

    @classmethod
    def from_result(cls, result: RankCheckResult) -> "OrganicResultResponse":
        return cls(
            position=result.position,
            title=result.title,
            url=result.url,
            hostname=result.hostname,
            displayed_url=result.displayed_url,
            snippet=result.snippet,
        )


class RankingResponse(BaseModel):
    tracked_site_id: UUID | None
    tracked_domain_id: UUID | None
    tracked_site_name: str
    matched_domain: str
    position: int
    result_url: str
    result_hostname: str
    title: str | None

    @classmethod
    def from_ranking(cls, ranking: Ranking) -> "RankingResponse":
        return cls(
            tracked_site_id=ranking.tracked_site_id,
            tracked_domain_id=ranking.tracked_domain_id,
            tracked_site_name=ranking.tracked_site_name_snapshot,
            matched_domain=ranking.matched_domain_snapshot,
            position=ranking.position,
            result_url=ranking.result_url,
            result_hostname=ranking.result_hostname,
            title=ranking.title,
        )


class ProviderAttemptResponse(BaseModel):
    provider: str
    attempt_number: int
    status: str
    started_at: datetime
    completed_at: datetime
    error_code: str | None
    provider_request_count: int

    @classmethod
    def from_attempt(
        cls, attempt: RankCheckProviderAttempt
    ) -> "ProviderAttemptResponse":
        return cls(
            provider=attempt.provider,
            attempt_number=attempt.attempt_number,
            status=attempt.status.value,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            error_code=attempt.error_code,
            provider_request_count=attempt.provider_request_count,
        )


class RankCheckResponse(BaseModel):
    id: UUID
    project_id: UUID
    keyword_id: UUID
    provider: str
    status: RankCheckStatus
    query_snapshot: str
    search_engine_snapshot: str
    country_code_snapshot: str
    language_code_snapshot: str
    device_snapshot: str
    location_snapshot: str | None
    result_limit: int
    provider_request_count: int
    provider_request_id: str | None
    requested_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    result_count: int
    rankings: list[RankingResponse]
    provider_attempts: list[ProviderAttemptResponse]
    created_at: datetime

    @classmethod
    def from_check(
        cls,
        check: RankCheck,
        results: list[RankCheckResult],
        rankings: list[Ranking],
        attempts: list[RankCheckProviderAttempt] | None = None,
    ) -> "RankCheckResponse":
        return cls(
            id=check.id,
            project_id=check.project_id,
            keyword_id=check.keyword_id,
            provider=check.provider,
            status=check.status,
            query_snapshot=check.query_snapshot,
            search_engine_snapshot=check.search_engine_snapshot,
            country_code_snapshot=check.country_code_snapshot,
            language_code_snapshot=check.language_code_snapshot,
            device_snapshot=check.device_snapshot,
            location_snapshot=check.location_snapshot,
            result_limit=check.result_limit,
            provider_request_count=check.provider_request_count,
            provider_request_id=check.provider_request_id,
            requested_at=check.requested_at,
            completed_at=check.completed_at,
            error_code=check.error_code,
            error_message=check.error_message,
            result_count=len(results),
            rankings=[RankingResponse.from_ranking(value) for value in rankings],
            provider_attempts=[
                ProviderAttemptResponse.from_attempt(value)
                for value in (attempts or [])
            ],
            created_at=check.created_at,
        )


class RankCheckDetailResponse(RankCheckResponse):
    organic_results: list[OrganicResultResponse]

    @classmethod
    def from_check_detail(
        cls,
        check: RankCheck,
        results: list[RankCheckResult],
        rankings: list[Ranking],
        attempts: list[RankCheckProviderAttempt] | None = None,
    ) -> "RankCheckDetailResponse":
        summary = RankCheckResponse.from_check(check, results, rankings, attempts)
        return cls(
            **summary.model_dump(),
            organic_results=[
                OrganicResultResponse.from_result(value) for value in results
            ],
        )


class RankCheckListResponse(BaseModel):
    items: list[RankCheckResponse]
    next_cursor: str | None
    has_more: bool


class ProjectRankCheckOutcome(BaseModel):
    keyword_id: UUID
    check: RankCheckResponse | None
    error_code: str | None = None


class ProjectRankCheckResponse(BaseModel):
    project_id: UUID
    submitted_keywords: int
    succeeded: int
    failed: int
    checks: list[ProjectRankCheckOutcome]


class LatestKeywordRanking(BaseModel):
    keyword_id: UUID
    keyword: str
    latest_check: RankCheckResponse | None


class LatestRankingResponse(BaseModel):
    items: list[LatestKeywordRanking]


RankCheckStatusFilter = Literal["pending", "running", "succeeded", "failed", "all"]
