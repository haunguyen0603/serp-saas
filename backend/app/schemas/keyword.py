from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.keyword import Keyword


class KeywordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keyword: str = Field(min_length=1, max_length=2048)


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
        return self


class KeywordResponse(BaseModel):
    id: UUID
    keyword: str
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_keyword(cls, keyword: Keyword) -> "KeywordResponse":
        return cls(
            id=keyword.id,
            keyword=keyword.keyword,
            active=keyword.active,
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
