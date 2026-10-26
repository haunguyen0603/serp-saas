from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AlertType = Literal["entered_top10", "left_top10", "rank_improved", "rank_declined"]


class AlertPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    enabled: bool = True
    notify_entered_top10: bool = True
    notify_left_top10: bool = True
    notify_improvement: bool = True
    notify_decline: bool = True
    movement_threshold: int = Field(default=3, ge=1, le=10, strict=True)
    email_enabled: bool = False


class AlertPreferencesResponse(AlertPreferences):
    email_available: bool


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    keyword_id: UUID
    tracked_site_id: UUID | None
    alert_type: AlertType
    previous_observation_id: UUID
    current_observation_id: UUID
    previous_rank: int | None
    current_rank: int | None
    rank_delta: int | None
    keyword: str
    project_name: str
    site_name: str
    device: str
    observed_at: datetime
    created_at: datetime
    read_at: datetime | None


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    next_cursor: str | None
    has_more: bool


class AlertTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
