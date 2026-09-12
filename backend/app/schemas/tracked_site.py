from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite, TrackedSiteStatus


class TrackedSiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=300)
    primary_domain: str = Field(min_length=1, max_length=2048)
    aliases: list[str] = Field(default_factory=list, max_length=1000)


class TrackedSiteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    status: TrackedSiteStatus | None = None

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def valid_status(cls, value: object) -> object:
        if value not in {TrackedSiteStatus.ACTIVE, TrackedSiteStatus.ARCHIVED}:
            raise PydanticCustomError(
                "INVALID_TRACKED_SITE_STATUS", "Tracked Site status is invalid."
            )
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class TrackedDomainCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    domain: str = Field(min_length=1, max_length=2048)
    make_primary: bool = False


class TrackedDomainUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    is_primary: bool | None = None
    active: bool | None = None

    @field_validator("is_primary", "active", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class TrackedDomainResponse(BaseModel):
    id: UUID
    domain: str
    is_primary: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, domain: TrackedDomain) -> "TrackedDomainResponse":
        return cls(
            id=domain.id,
            domain=domain.domain,
            is_primary=domain.is_primary,
            active=domain.active,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )


class TrackedSiteResponse(BaseModel):
    id: UUID
    name: str
    status: TrackedSiteStatus
    primary_domain: str | None
    domain_alias_count: int
    domains: list[TrackedDomainResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_site(
        cls, site: TrackedSite, domains: list[TrackedDomain]
    ) -> "TrackedSiteResponse":
        ordered = sorted(domains, key=lambda item: (not item.is_primary, item.domain))
        primary = next((item.domain for item in ordered if item.is_primary), None)
        return cls(
            id=site.id,
            name=site.name,
            status=site.status,
            primary_domain=primary,
            domain_alias_count=max(0, len(ordered) - (1 if primary else 0)),
            domains=[TrackedDomainResponse.from_domain(item) for item in ordered],
            created_at=site.created_at,
            updated_at=site.updated_at,
        )


class TrackedSiteListResponse(BaseModel):
    items: list[TrackedSiteResponse]
    next_cursor: str | None
    has_more: bool


TrackedSiteStatusFilter = Literal["active", "archived", "all"]
