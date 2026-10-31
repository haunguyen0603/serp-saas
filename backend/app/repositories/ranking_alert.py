from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, literal, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.project import Project
from app.models.ranking_alert import RankingAlert, RankingAlertPreference
from app.schemas.ranking_alert import AlertListResponse, AlertPreferences, AlertResponse
from app.services.normalization import decode_cursor, encode_cursor


class RankingAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project(
        self, project_id: UUID, user_id: UUID, *, lock: bool = False
    ) -> Project:
        query = select(Project).where(
            Project.id == project_id, Project.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        project = await self.session.scalar(query)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        return project

    async def preferences(self, project_id: UUID, user_id: UUID) -> AlertPreferences:
        await self.project(project_id, user_id)
        row = await self.session.scalar(
            select(RankingAlertPreference).where(
                RankingAlertPreference.project_id == project_id,
                RankingAlertPreference.user_id == user_id,
            )
        )
        return AlertPreferences.model_validate(row) if row else AlertPreferences()

    async def put_preferences(
        self, project_id: UUID, user_id: UUID, data: AlertPreferences
    ) -> AlertPreferences:
        await self.project(project_id, user_id, lock=True)
        await self.session.execute(
            insert(RankingAlertPreference)
            .values(user_id=user_id, project_id=project_id, **data.model_dump())
            .on_conflict_do_update(
                constraint="uq_ranking_alert_preferences_owner",
                set_={
                    **data.model_dump(),
                    "updated_at": datetime.now(UTC),
                },
            )
        )
        return data

    async def inbox(
        self,
        user_id: UUID,
        project_id: UUID | None,
        unread_only: bool,
        limit: int,
        cursor: str | None,
    ) -> AlertListResponse:
        query = select(RankingAlert).where(RankingAlert.user_id == user_id)
        if project_id:
            await self.project(project_id, user_id)
            query = query.where(RankingAlert.project_id == project_id)
        if unread_only:
            query = query.where(RankingAlert.read_at.is_(None))
        decoded = decode_cursor(cursor)
        if decoded:
            query = query.where(
                tuple_(RankingAlert.created_at, RankingAlert.id)
                < tuple_(literal(decoded[0]), literal(decoded[1]))
            )
        rows = list(
            await self.session.scalars(
                query.order_by(
                    RankingAlert.created_at.desc(), RankingAlert.id.desc()
                ).limit(limit + 1)
            )
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return AlertListResponse(
            items=[AlertResponse.model_validate(row) for row in rows],
            has_more=more,
            next_cursor=encode_cursor(rows[-1].created_at, rows[-1].id)
            if more
            else None,
        )

    async def unread_count(self, user_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(RankingAlert)
                .where(RankingAlert.user_id == user_id, RankingAlert.read_at.is_(None))
            )
            or 0
        )

    async def read(self, user_id: UUID, alert_id: UUID) -> AlertResponse:
        row = await self.session.scalar(
            update(RankingAlert)
            .where(RankingAlert.id == alert_id, RankingAlert.user_id == user_id)
            .values(read_at=func.coalesce(RankingAlert.read_at, datetime.now(UTC)))
            .returning(RankingAlert)
        )
        if row is None:
            raise AppError(404, "RANKING_ALERT_NOT_FOUND", "Ranking alert not found.")
        return AlertResponse.model_validate(row)

    async def read_all(self, user_id: UUID, project_id: UUID | None) -> None:
        query = update(RankingAlert).where(
            RankingAlert.user_id == user_id, RankingAlert.read_at.is_(None)
        )
        if project_id:
            await self.project(project_id, user_id)
            query = query.where(RankingAlert.project_id == project_id)
        await self.session.execute(query.values(read_at=datetime.now(UTC)))
