from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=200)


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=200)


class KeywordGroupResponse(BaseModel):
    id: UUID
    name: str
    active_keyword_count: int
    created_at: datetime
    updated_at: datetime


class KeywordTagResponse(BaseModel):
    id: UUID
    name: str
    active_keyword_count: int
    created_at: datetime
    updated_at: datetime


class KeywordGroupListResponse(BaseModel):
    items: list[KeywordGroupResponse]


class KeywordTagListResponse(BaseModel):
    items: list[KeywordTagResponse]


BulkOrganizationOperation = Literal[
    "assign_group",
    "add_tags",
    "remove_tags",
    "replace_tags",
    "archive",
    "restore",
]


class KeywordBulkOrganization(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keyword_ids: list[UUID] = Field(min_length=1, max_length=200)
    operation: BulkOrganizationOperation
    group_id: UUID | None = None
    tag_ids: list[UUID] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def operation_arguments(self) -> Self:
        supplied_group = "group_id" in self.model_fields_set
        supplied_tags = "tag_ids" in self.model_fields_set
        if self.operation == "assign_group":
            if not supplied_group or supplied_tags:
                raise ValueError("assign_group requires only group_id")
        elif self.operation in {"add_tags", "remove_tags"}:
            if not supplied_tags or not self.tag_ids or supplied_group:
                raise ValueError(f"{self.operation} requires non-empty tag_ids")
        elif self.operation == "replace_tags":
            if not supplied_tags or self.tag_ids is None or supplied_group:
                raise ValueError("replace_tags requires tag_ids")
        elif supplied_group or supplied_tags:
            raise ValueError(f"{self.operation} does not accept organization IDs")
        return self


class KeywordBulkOrganizationResult(BaseModel):
    operation: BulkOrganizationOperation
    selected_count: int
    affected_keyword_count: int
    assignment_count: int | None = None
