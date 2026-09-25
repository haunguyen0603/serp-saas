from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReportPeriod = Literal["7d", "30d", "90d", "custom"]
ReportTypeValue = Literal["comparison_csv", "history_csv", "project_pdf"]
TagMatch = Literal["any", "all"]


class ReportDefinition(BaseModel):
    period: ReportPeriod = "30d"
    start_date: date | None = None
    end_date: date | None = None
    tracked_site_id: UUID | None = None
    keyword_group_id: UUID | None = None
    keyword_tag_ids: list[UUID] = Field(default_factory=list, max_length=100)
    tag_match: TagMatch = "any"
    include_keyword_details: bool = True

    @model_validator(mode="after")
    def validate_period(self) -> "ReportDefinition":
        if self.period == "custom":
            if self.start_date is None or self.end_date is None:
                raise ValueError("Custom reports require start_date and end_date")
            if self.start_date > self.end_date:
                raise ValueError("start_date must not be after end_date")
        elif self.start_date is not None or self.end_date is not None:
            raise ValueError(
                "start_date and end_date are only valid for custom reports"
            )
        if len(set(self.keyword_tag_ids)) != len(self.keyword_tag_ids):
            raise ValueError("keyword_tag_ids must not contain duplicates")
        return self


class ReportCreateRequest(ReportDefinition):
    report_type: ReportTypeValue
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class ReportObservation(BaseModel):
    checked_at_utc: datetime
    position: int | None
    depth: int
    status: Literal["ranked", "not_found_in_depth"]


class ReportPreviewRow(BaseModel):
    keyword_id: UUID
    keyword: str
    tracked_site_id: UUID
    tracked_site_name: str
    comparison: ReportObservation | None
    current: ReportObservation | None
    movement_type: str
    numeric_change: int | None


class ReportMetrics(BaseModel):
    distinct_keywords: int
    keyword_site_pairs: int
    distinct_tracked_sites: int
    observed_pairs: int
    never_checked: int
    effective_depth: int
    latest_successful_check_at: datetime | None
    comparison_basis: str
    distribution: dict[str, int]
    movements: dict[str, int]
    biggest_winners: list[ReportPreviewRow] = Field(default_factory=list)
    biggest_losers: list[ReportPreviewRow] = Field(default_factory=list)


class ReportPreviewResponse(BaseModel):
    project_id: UUID
    project_name: str
    device: str
    period_start_utc: datetime
    period_end_utc: datetime
    report_timezone: Literal["UTC"] = "UTC"
    active_scope: Literal["active_keywords_and_tracked_sites"] = (
        "active_keywords_and_tracked_sites"
    )
    no_matching_keywords: bool
    matching_keywords_without_observations: bool
    filters: dict[str, object]
    metrics: ReportMetrics
    sample: list[ReportPreviewRow]


class GeneratedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    report_schedule_id: UUID | None
    report_type: str
    status: str
    period_start_utc: datetime
    period_end_utc: datetime
    filters_snapshot: dict[str, object]
    metrics_snapshot: dict[str, object] | None
    schema_version: int
    mime_type: str | None
    byte_size: int | None
    filename: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime
    error_code: str | None
    attempt_count: int


class GeneratedReportList(BaseModel):
    items: list[GeneratedReportResponse]
    next_cursor: str | None
    has_more: bool


class DeliveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generated_report_id: UUID
    status: str
    attempt_number: int
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None


class ReportScheduleRequest(ReportDefinition):
    name: str = Field(min_length=1, max_length=200)
    frequency: Literal["weekly", "monthly"]
    scheduled_hour: int = Field(ge=0, le=23)
    weekday: int | None = Field(default=None, ge=0, le=6)
    month_day: int | None = Field(default=None, ge=1, le=31)
    active: bool = True

    @model_validator(mode="after")
    def validate_calendar(self) -> "ReportScheduleRequest":
        if self.period != "30d" or self.start_date or self.end_date:
            raise ValueError("Scheduled reports resolve their own completed period")
        if self.frequency == "weekly":
            if self.weekday is None or self.month_day is not None:
                raise ValueError("Weekly schedules require weekday only")
        elif self.month_day is None or self.weekday is not None:
            raise ValueError("Monthly schedules require month_day only")
        return self


class ReportScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    frequency: Literal["weekly", "monthly"] | None = None
    scheduled_hour: int | None = Field(default=None, ge=0, le=23)
    weekday: int | None = Field(default=None, ge=0, le=6)
    month_day: int | None = Field(default=None, ge=1, le=31)
    active: bool | None = None
    tracked_site_id: UUID | None = None
    keyword_group_id: UUID | None = None
    keyword_tag_ids: list[UUID] | None = Field(default=None, max_length=100)
    tag_match: TagMatch | None = None
    include_keyword_details: bool | None = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    report_type: str
    frequency: str
    report_timezone: str
    scheduled_hour: int
    weekday: int | None
    month_day: int | None
    filters: dict[str, object]
    active: bool
    delivery_configured: bool
    recipient_mode: Literal["verified_account"] = "verified_account"
    next_run_at_utc: datetime
    last_run_at_utc: datetime | None
    last_delivery_status: str | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime


class ReportScheduleList(BaseModel):
    items: list[ReportScheduleResponse]
    delivery_configured: bool
    recipient_mode: Literal["verified_account"] = "verified_account"


class ReportTaskPayload(BaseModel):
    version: Literal[1]
    report_id: UUID
