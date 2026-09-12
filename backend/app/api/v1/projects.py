from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.auth import CurrentUser
from app.dependencies.business import Projects
from app.schemas.health import ErrorResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectCreateResult,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusFilter,
    ProjectUpdate,
)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.post("", status_code=201, response_model=ProjectCreateResult)
async def create_project(
    data: ProjectCreate, user: CurrentUser, projects: Projects
) -> ProjectCreateResult:
    return await projects.create(user.id, data)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user: CurrentUser,
    projects: Projects,
    status: ProjectStatusFilter = "active",
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> ProjectListResponse:
    return await projects.list(
        user.id, status=status, search=search, limit=limit, cursor=cursor
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, user: CurrentUser, projects: Projects
) -> ProjectResponse:
    return await projects.response(project_id, user.id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    user: CurrentUser,
    projects: Projects,
) -> ProjectResponse:
    return await projects.update_response(project_id, user.id, data)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID, user: CurrentUser, projects: Projects
) -> Response:
    await projects.delete(project_id, user.id)
    return Response(status_code=204)
