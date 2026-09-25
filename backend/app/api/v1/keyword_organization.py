from uuid import UUID

from fastapi import APIRouter, Response

from app.dependencies.auth import CurrentUser
from app.dependencies.business import KeywordOrganizations
from app.schemas.keyword_organization import (
    KeywordBulkOrganization,
    KeywordBulkOrganizationResult,
    KeywordGroupListResponse,
    KeywordGroupResponse,
    KeywordTagListResponse,
    KeywordTagResponse,
    OrganizationCreate,
    OrganizationUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["keyword-organization"],
)


@router.get("/keyword-groups", response_model=KeywordGroupListResponse)
async def list_keyword_groups(
    project_id: UUID,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordGroupListResponse:
    return await service.list_groups(project_id, current_user.id)


@router.post("/keyword-groups", status_code=201, response_model=KeywordGroupResponse)
async def create_keyword_group(
    project_id: UUID,
    data: OrganizationCreate,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordGroupResponse:
    return await service.create_group(project_id, current_user.id, data)


@router.patch("/keyword-groups/{group_id}", response_model=KeywordGroupResponse)
async def update_keyword_group(
    project_id: UUID,
    group_id: UUID,
    data: OrganizationUpdate,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordGroupResponse:
    return await service.update_group(project_id, group_id, current_user.id, data)


@router.delete("/keyword-groups/{group_id}", status_code=204)
async def delete_keyword_group(
    project_id: UUID,
    group_id: UUID,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> Response:
    await service.delete_group(project_id, group_id, current_user.id)
    return Response(status_code=204)


@router.get("/keyword-tags", response_model=KeywordTagListResponse)
async def list_keyword_tags(
    project_id: UUID,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordTagListResponse:
    return await service.list_tags(project_id, current_user.id)


@router.post("/keyword-tags", status_code=201, response_model=KeywordTagResponse)
async def create_keyword_tag(
    project_id: UUID,
    data: OrganizationCreate,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordTagResponse:
    return await service.create_tag(project_id, current_user.id, data)


@router.patch("/keyword-tags/{tag_id}", response_model=KeywordTagResponse)
async def update_keyword_tag(
    project_id: UUID,
    tag_id: UUID,
    data: OrganizationUpdate,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordTagResponse:
    return await service.update_tag(project_id, tag_id, current_user.id, data)


@router.delete("/keyword-tags/{tag_id}", status_code=204)
async def delete_keyword_tag(
    project_id: UUID,
    tag_id: UUID,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> Response:
    await service.delete_tag(project_id, tag_id, current_user.id)
    return Response(status_code=204)


@router.post("/keywords/bulk-organize", response_model=KeywordBulkOrganizationResult)
async def bulk_organize_keywords(
    project_id: UUID,
    data: KeywordBulkOrganization,
    current_user: CurrentUser,
    service: KeywordOrganizations,
) -> KeywordBulkOrganizationResult:
    return await service.bulk_organize(project_id, current_user.id, data)
