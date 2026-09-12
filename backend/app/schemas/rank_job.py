from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword_ids: list[UUID] | None = Field(default=None, max_length=5000)


class TaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    job_id: UUID


class BatchAccepted(BaseModel):
    batch_id: UUID
    job_id: UUID | None = None
    status: str
    requested_keyword_count: int


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    trigger_type: str
    requested_keyword_count: int
    queued_keyword_count: int = 0
    running_keyword_count: int = 0
    succeeded_keyword_count: int = 0
    failed_keyword_count: int = 0
    cancelled_keyword_count: int = 0
    progress_percent: float = 0
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    keyword_id: UUID
    keyword: str = ""
    status: str
    attempt_count: int
    rank_check_id: UUID | None
    last_error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None


class BatchList(BaseModel):
    items: list[BatchResponse]
    next_cursor: str | None
    has_more: bool


class JobList(BaseModel):
    items: list[JobResponse]
    next_cursor: str | None
    has_more: bool


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    frequency: Literal["daily", "weekly"]
    local_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(max_length=100)
    weekday: int = Field(default=0, ge=0, le=6)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone") from None
        return value


class ScheduleResponse(ScheduleRequest):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    next_run_at: datetime
    last_enqueued_at: datetime | None
