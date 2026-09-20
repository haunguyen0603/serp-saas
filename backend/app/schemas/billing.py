from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Device = Literal["desktop", "mobile"]


class ActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_code: str = Field(max_length=64)
    period_start: AwareDatetime
    period_end: AwareDatetime
    payment_method: Literal["manual_bank_transfer"] | None = None
    payment_reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    replace_existing: bool = False


class ExtendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period_end: AwareDatetime


class AdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_scope: Device
    amount: int = Field(ge=-10000000, le=10000000)
    note: str = Field(min_length=1, max_length=2000)


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    device_scope: str
    price_monthly_minor_units: int
    currency: str
    max_projects: int
    max_keywords: int
    monthly_keyword_checks: int
    scheduled_checks_enabled: bool
    max_scheduled_frequency: str


class AdminPlanResponse(PlanResponse):
    updated_at: datetime


class PlanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: AwareDatetime
    price_monthly_minor_units: int = Field(strict=True, ge=0, le=2147483647)
    max_projects: int = Field(strict=True, ge=0, le=2147483647)
    max_keywords: int = Field(strict=True, ge=0, le=2147483647)
    monthly_keyword_checks: int = Field(strict=True, ge=0, le=2147483647)


class PlanChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plan_id: UUID
    actor_user_id: UUID | None
    before: dict[str, Any]
    after: dict[str, Any]
    created_at: datetime


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    device_scope: str
    status: str
    source: str
    period_start: datetime
    period_end: datetime
    snapshot: dict[str, Any]
    payment_method: str | None
    payment_reference: str | None
    payment_note: str | None
    activated_at: datetime | None
    activated_by_user_id: UUID | None
    cancelled_at: datetime | None
    created_at: datetime
