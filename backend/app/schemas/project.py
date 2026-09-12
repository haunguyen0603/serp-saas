from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.project import Project, ProjectStatus


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=300)
    search_engine: str = "google"
    country_code: str = "US"
    language_code: str = "en"
    device: str = "desktop"
    location: str | None = Field(default=None, max_length=1000)
    keywords: list[str] = Field(min_length=1)

    @field_validator("keywords")
    @classmethod
    def keyword_limit(cls, value: list[str]) -> list[str]:
        if len(value) > 1000:
            raise PydanticCustomError(
                "PROJECT_KEYWORD_LIMIT_EXCEEDED",
                "A Project may contain at most 1000 initial keyword inputs.",
            )
        return value


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    search_engine: str | None = None
    country_code: str | None = None
    language_code: str | None = None
    device: str | None = None
    location: str | None = Field(default=None, max_length=1000)
    status: ProjectStatus | None = None

    @field_validator(
        "name",
        "search_engine",
        "country_code",
        "language_code",
        "device",
        mode="before",
    )
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def valid_status(cls, value: object) -> object:
        if value not in {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED}:
            raise PydanticCustomError(
                "INVALID_PROJECT_STATUS", "Project status is invalid."
            )
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None
    status: ProjectStatus
    keyword_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_project(cls, project: Project, keyword_count: int) -> "ProjectResponse":
        return cls(
            id=project.id,
            name=project.name,
            search_engine=project.search_engine,
            country_code=project.country_code,
            language_code=project.language_code,
            device=project.device,
            location=project.location,
            status=project.status,
            keyword_count=keyword_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class InitialKeywordResult(BaseModel):
    submitted: int
    normalized_unique: int
    created: int
    skipped_duplicates: int
    skipped_empty: int


class ProjectCreateResult(BaseModel):
    project: ProjectResponse
    keywords: InitialKeywordResult


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    next_cursor: str | None
    has_more: bool


ProjectStatusFilter = Literal["active", "archived", "all"]
