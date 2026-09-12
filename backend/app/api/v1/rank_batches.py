from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from app.dependencies.auth import CurrentUser
from app.schemas.rank_job import (
    BatchAccepted,
    BatchList,
    BatchRequest,
    BatchResponse,
    JobList,
    ScheduleRequest,
    ScheduleResponse,
)
from app.services.rank_batches import RankBatchService
from app.services.rank_schedules import RankScheduleService

router = APIRouter(
    prefix="/projects",
    tags=["rank-check-batches"],
    responses={401: {}, 404: {}, 422: {}},
)


def get_batches(request: Request) -> RankBatchService:
    return RankBatchService(
        request.app.state.session_factory,
        request.app.state.settings,
        request.app.state.task_queue,
    )


Batches = Annotated[RankBatchService, Depends(get_batches)]


@router.post("/{project_id}/rank-check-batches", status_code=202)
async def create_batch(
    project_id: UUID,
    current_user: CurrentUser,
    service: Batches,
    request: Annotated[BatchRequest, Body(default_factory=BatchRequest)],
) -> BatchAccepted:
    return await service.create(project_id, current_user.id, request.keyword_ids)


@router.post("/{project_id}/keywords/{keyword_id}/rank-check-batches", status_code=202)
async def create_keyword_batch(
    project_id: UUID,
    keyword_id: UUID,
    current_user: CurrentUser,
    service: Batches,
    request: Annotated[BatchRequest, Body(default_factory=BatchRequest)],
) -> BatchAccepted:
    if request.keyword_ids is not None:
        from app.core.errors import AppError

        raise AppError(
            422, "INVALID_REQUEST", "Keyword selection is not accepted here."
        )
    return await service.create(
        project_id, current_user.id, [keyword_id], "manual_keyword"
    )


@router.get("/{project_id}/rank-check-batches")
async def batch_history(
    project_id: UUID,
    current_user: CurrentUser,
    service: Batches,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> BatchList:
    return await service.history(project_id, current_user.id, limit, cursor)


@router.get("/{project_id}/rank-check-batches/{batch_id}")
async def batch_detail(
    project_id: UUID, batch_id: UUID, current_user: CurrentUser, service: Batches
) -> BatchResponse:
    return await service.detail(project_id, current_user.id, batch_id)


@router.get("/{project_id}/rank-check-batches/{batch_id}/jobs")
async def batch_jobs(
    project_id: UUID,
    batch_id: UUID,
    current_user: CurrentUser,
    service: Batches,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> JobList:
    return await service.jobs(project_id, current_user.id, batch_id, limit, cursor)


@router.post("/{project_id}/rank-check-batches/{batch_id}/cancel")
async def cancel_batch(
    project_id: UUID, batch_id: UUID, current_user: CurrentUser, service: Batches
) -> BatchResponse:
    return await service.cancel(project_id, current_user.id, batch_id)


@router.get("/{project_id}/rank-schedule")
async def get_schedule(
    project_id: UUID, current_user: CurrentUser, service: Batches
) -> ScheduleResponse | None:
    return await RankScheduleService(service).get(project_id, current_user.id)


@router.put("/{project_id}/rank-schedule")
async def put_schedule(
    project_id: UUID,
    current_user: CurrentUser,
    service: Batches,
    request: ScheduleRequest,
) -> ScheduleResponse:
    return await RankScheduleService(service).put(project_id, current_user.id, request)


@router.delete("/{project_id}/rank-schedule", status_code=204)
async def delete_schedule(
    project_id: UUID, current_user: CurrentUser, service: Batches
) -> Response:
    await RankScheduleService(service).delete(project_id, current_user.id)
    return Response(status_code=204)
