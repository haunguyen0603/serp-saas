from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.keyword import Keyword
from app.models.keyword_organization import KeywordGroup, KeywordTag


class KeywordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keyword: str = Field(min_length=1, max_length=2048)
    group_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list, max_length=100)


class KeywordBulkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keywords: list[str] = Field(min_length=1)

    @field_validator("keywords")
    @classmethod
    def bulk_limit(cls, value: list[str]) -> list[str]:
        if len(value) > 1000:
            raise PydanticCustomError(
                "BULK_KEYWORD_LIMIT_EXCEEDED",
                "A bulk request may contain at most 1000 keywords.",
            )
        return value


class KeywordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keyword: str | None = Field(default=None, min_length=1, max_length=2048)
    active: bool | None = None
    group_id: UUID | None = None
    tag_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("keyword", "active", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if "tag_ids" in self.model_fields_set and self.tag_ids is None:
            raise ValueError("tag_ids cannot be null")
        return self


class KeywordOrganizationRef(BaseModel):
    id: UUID
    name: str


class KeywordResponse(BaseModel):
    id: UUID
    keyword: str
    active: bool
    group: KeywordOrganizationRef | None
    tags: list[KeywordOrganizationRef]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_keyword(
        cls,
        keyword: Keyword,
        *,
        group: KeywordGroup | None = None,
        tags: list[KeywordTag] | None = None,
    ) -> "KeywordResponse":
        if group is None:
            group = keyword.__dict__.get("group")
        if tags is None:
            tags = keyword.__dict__.get("tags", [])
        return cls(
            id=keyword.id,
            keyword=keyword.keyword,
            active=keyword.active,
            group=(
                KeywordOrganizationRef(id=group.id, name=group.name)
                if group is not None
                else None
            ),
            tags=[
                KeywordOrganizationRef(id=tag.id, name=tag.name) for tag in (tags or [])
            ],
            created_at=keyword.created_at,
            updated_at=keyword.updated_at,
        )


class KeywordListResponse(BaseModel):
    items: list[KeywordResponse]
    next_cursor: str | None
    has_more: bool


class KeywordBulkResult(BaseModel):
    submitted: int
    normalized_unique: int
    created: int
    skipped_duplicates: int
    skipped_empty: int
    items: list[KeywordResponse]


KeywordActiveFilter = Literal["true", "false", "all"]
