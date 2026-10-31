from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.auth import AppSettings, CurrentUser, DBSession
from app.repositories.ranking_alert import RankingAlertRepository
from app.schemas.ranking_alert import (
    AlertListResponse,
    AlertPreferences,
    AlertPreferencesResponse,
    AlertResponse,
)

router = APIRouter(tags=["ranking-alerts"])


@router.get("/ranking-alerts", response_model=AlertListResponse)
async def inbox(
    user: CurrentUser,
    session: DBSession,
    project_id: UUID | None = None,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> AlertListResponse:
    return await RankingAlertRepository(session).inbox(
        user.id, project_id, unread_only, limit, cursor
    )


@router.get("/ranking-alerts/unread-count")
async def unread_count(user: CurrentUser, session: DBSession) -> dict[str, int]:
    return {"count": await RankingAlertRepository(session).unread_count(user.id)}


@router.post("/ranking-alerts/mark-all-read", status_code=204)
async def mark_all_read(
    user: CurrentUser, session: DBSession, project_id: UUID | None = None
) -> Response:
    await RankingAlertRepository(session).read_all(user.id, project_id)
    return Response(status_code=204)


@router.patch("/ranking-alerts/{alert_id}/read", response_model=AlertResponse)
async def mark_read(
    alert_id: UUID, user: CurrentUser, session: DBSession
) -> AlertResponse:
    return await RankingAlertRepository(session).read(user.id, alert_id)


def preference_response(
    data: AlertPreferences, settings: AppSettings
) -> AlertPreferencesResponse:
    return AlertPreferencesResponse(
        **data.model_dump(),
        email_available=(
            settings.ranking_alert_email_enabled
            and settings.auth_email_provider != "disabled"
        ),
    )


@router.get(
    "/projects/{project_id}/ranking-alert-preferences",
    response_model=AlertPreferencesResponse,
)
async def get_preferences(
    project_id: UUID, user: CurrentUser, session: DBSession, settings: AppSettings
) -> AlertPreferencesResponse:
    return preference_response(
        await RankingAlertRepository(session).preferences(project_id, user.id), settings
    )


@router.put(
    "/projects/{project_id}/ranking-alert-preferences",
    response_model=AlertPreferencesResponse,
)
async def put_preferences(
    project_id: UUID,
    data: AlertPreferences,
    user: CurrentUser,
    session: DBSession,
    settings: AppSettings,
) -> AlertPreferencesResponse:
    return preference_response(
        await RankingAlertRepository(session).put_preferences(
            project_id, user.id, data
        ),
        settings,
    )
