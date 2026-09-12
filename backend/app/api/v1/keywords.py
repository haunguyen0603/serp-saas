from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.auth import CurrentUser
from app.dependencies.business import Keywords
from app.schemas.health import ErrorResponse
from app.schemas.keyword import (
    KeywordActiveFilter,
    KeywordBulkCreate,
    KeywordBulkResult,
    KeywordCreate,
    KeywordListResponse,
    KeywordResponse,
    KeywordUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/keywords",
    tags=["keywords"],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.post("", status_code=201, response_model=KeywordResponse)
async def create_keyword(
    project_id: UUID,
    data: KeywordCreate,
    user: CurrentUser,
    keywords: Keywords,
) -> KeywordResponse:
    return KeywordResponse.from_keyword(
        await keywords.create(project_id, user.id, data)
    )


@router.post("/bulk", status_code=201, response_model=KeywordBulkResult)
async def bulk_create_keywords(
    project_id: UUID,
    data: KeywordBulkCreate,
    user: CurrentUser,
    keywords: Keywords,
) -> KeywordBulkResult:
    return await keywords.bulk_create(project_id, user.id, data)


@router.get("", response_model=KeywordListResponse)
async def list_keywords(
    project_id: UUID,
    user: CurrentUser,
    keywords: Keywords,
    search: Annotated[str | None, Query(max_length=512)] = None,
    active: KeywordActiveFilter = "true",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> KeywordListResponse:
    return await keywords.list(
        project_id,
        user.id,
        search=search,
        active=active,
        limit=limit,
        cursor=cursor,
    )


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
    project_id: UUID,
    keyword_id: UUID,
    user: CurrentUser,
    keywords: Keywords,
) -> KeywordResponse:
    return KeywordResponse.from_keyword(
        await keywords.get(keyword_id, project_id, user.id)
    )


@router.patch("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    project_id: UUID,
    keyword_id: UUID,
    data: KeywordUpdate,
    user: CurrentUser,
    keywords: Keywords,
) -> KeywordResponse:
    return KeywordResponse.from_keyword(
        await keywords.update(keyword_id, project_id, user.id, data)
    )


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(
    project_id: UUID,
    keyword_id: UUID,
    user: CurrentUser,
    keywords: Keywords,
) -> Response:
    await keywords.delete(keyword_id, project_id, user.id)
    return Response(status_code=204)
