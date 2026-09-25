from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.errors import AppError
from app.dependencies.auth import CurrentUser
from app.schemas.report import (
    DeliveryAttemptResponse,
    GeneratedReportList,
    GeneratedReportResponse,
    ReportCreateRequest,
    ReportDefinition,
    ReportPreviewResponse,
    ReportScheduleList,
    ReportScheduleRequest,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)
from app.services.reports import ReportScheduleService, ReportService

router = APIRouter(prefix="/projects", tags=["reports"])


def get_reports(request: Request) -> ReportService:
    return ReportService(
        request.app.state.session_factory,
        request.app.state.settings,
        request.app.state.task_queue,
        request.app.state.report_storage,
        request.app.state.report_email_sender,
    )


Reports = Annotated[ReportService, Depends(get_reports)]


def _tag_ids(value: str | None) -> list[UUID]:
    if not value:
        return []
    try:
        result = [UUID(part) for part in value.split(",") if part]
    except ValueError:
        raise AppError(
            422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid."
        ) from None
    if not result or len(result) > 100 or len(set(result)) != len(result):
        raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
    return result


@router.get("/{project_id}/reports/preview")
async def preview_report(
    project_id: UUID,
    current_user: CurrentUser,
    service: Reports,
    period: str = "30d",
    start_date: date | None = None,
    end_date: date | None = None,
    tracked_site_id: UUID | None = None,
    keyword_group_id: UUID | None = None,
    keyword_tag_ids: str | None = None,
    tag_match: str = "any",
    include_keyword_details: bool = True,
) -> ReportPreviewResponse:
    try:
        definition = ReportDefinition.model_validate(
            {
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "tracked_site_id": tracked_site_id,
                "keyword_group_id": keyword_group_id,
                "keyword_tag_ids": _tag_ids(keyword_tag_ids),
                "tag_match": tag_match,
                "include_keyword_details": include_keyword_details,
            }
        )
    except ValueError:
        raise AppError(
            422, "INVALID_REPORT_RANGE", "Report parameters are invalid."
        ) from None
    return await service.preview(project_id, current_user.id, definition)


@router.post("/{project_id}/reports", status_code=202)
async def create_report(
    project_id: UUID,
    current_user: CurrentUser,
    service: Reports,
    payload: ReportCreateRequest,
) -> GeneratedReportResponse:
    return await service.create(project_id, current_user.id, payload)


@router.get("/{project_id}/reports")
async def list_reports(
    project_id: UUID,
    current_user: CurrentUser,
    service: Reports,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> GeneratedReportList:
    return await service.recent(project_id, current_user.id, limit, cursor)


@router.get("/{project_id}/reports/{report_id}")
async def report_detail(
    project_id: UUID,
    report_id: UUID,
    current_user: CurrentUser,
    service: Reports,
) -> GeneratedReportResponse:
    return await service.detail(project_id, current_user.id, report_id)


@router.get("/{project_id}/reports/{report_id}/download")
async def download_report(
    project_id: UUID,
    report_id: UUID,
    current_user: CurrentUser,
    service: Reports,
) -> Response:
    data, mime_type, filename = await service.download(
        project_id, current_user.id, report_id
    )
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{project_id}/reports/{report_id}/retry", status_code=202)
async def retry_report(
    project_id: UUID,
    report_id: UUID,
    current_user: CurrentUser,
    service: Reports,
) -> GeneratedReportResponse:
    return await service.retry(project_id, current_user.id, report_id)


@router.get("/{project_id}/reports/{report_id}/delivery-attempts")
async def report_delivery_attempts(
    project_id: UUID,
    report_id: UUID,
    current_user: CurrentUser,
    service: Reports,
) -> list[DeliveryAttemptResponse]:
    return await service.delivery_attempts(project_id, current_user.id, report_id)


@router.get("/{project_id}/report-schedules")
async def list_report_schedules(
    project_id: UUID, current_user: CurrentUser, service: Reports
) -> ReportScheduleList:
    return await ReportScheduleService(service).list(project_id, current_user.id)


@router.post("/{project_id}/report-schedules", status_code=201)
async def create_report_schedule(
    project_id: UUID,
    current_user: CurrentUser,
    service: Reports,
    payload: ReportScheduleRequest,
) -> ReportScheduleResponse:
    return await ReportScheduleService(service).create(
        project_id, current_user.id, payload
    )


@router.patch("/{project_id}/report-schedules/{schedule_id}")
async def update_report_schedule(
    project_id: UUID,
    schedule_id: UUID,
    current_user: CurrentUser,
    service: Reports,
    payload: ReportScheduleUpdate,
) -> ReportScheduleResponse:
    return await ReportScheduleService(service).update(
        project_id, current_user.id, schedule_id, payload
    )


@router.delete("/{project_id}/report-schedules/{schedule_id}", status_code=204)
async def delete_report_schedule(
    project_id: UUID,
    schedule_id: UUID,
    current_user: CurrentUser,
    service: Reports,
) -> Response:
    await ReportScheduleService(service).delete(
        project_id, current_user.id, schedule_id
    )
    return Response(status_code=204)
