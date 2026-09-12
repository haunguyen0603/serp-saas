from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rank_check import RankCheck, RankCheckStatus


class RankCheckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_running(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        keyword_id: UUID,
        provider: str,
        query: str,
        search_engine: str,
        country_code: str,
        language_code: str,
        device: str,
        location: str | None,
        result_limit: int,
        requested_at: datetime,
    ) -> RankCheck:
        check = RankCheck(
            user_id=user_id,
            project_id=project_id,
            keyword_id=keyword_id,
            provider=provider,
            status=RankCheckStatus.PENDING,
            query_snapshot=query,
            search_engine_snapshot=search_engine,
            country_code_snapshot=country_code,
            language_code_snapshot=language_code,
            device_snapshot=device,
            location_snapshot=location,
            result_limit=result_limit,
            requested_at=requested_at,
        )
        self.session.add(check)
        await self.session.flush()
        check.status = RankCheckStatus.RUNNING
        await self.session.flush()
        return check

    async def get_owned(
        self,
        check_id: UUID,
        project_id: UUID,
        user_id: UUID,
        *,
        keyword_id: UUID | None = None,
        for_update: bool = False,
    ) -> RankCheck | None:
        statement = select(RankCheck).where(
            RankCheck.id == check_id,
            RankCheck.project_id == project_id,
            RankCheck.user_id == user_id,
        )
        if keyword_id is not None:
            statement = statement.where(RankCheck.keyword_id == keyword_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(RankCheck | None, await self.session.scalar(statement))

    async def list_history(
        self,
        project_id: UUID,
        keyword_id: UUID,
        user_id: UUID,
        *,
        status: RankCheckStatus | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> tuple[list[RankCheck], bool]:
        statement = select(RankCheck).where(
            RankCheck.project_id == project_id,
            RankCheck.keyword_id == keyword_id,
            RankCheck.user_id == user_id,
        )
        if status is not None:
            statement = statement.where(RankCheck.status == status)
        if cursor:
            created_at, item_id = cursor
            statement = statement.where(
                or_(
                    RankCheck.created_at < created_at,
                    and_(
                        RankCheck.created_at == created_at,
                        RankCheck.id < item_id,
                    ),
                )
            )
        statement = statement.order_by(
            RankCheck.created_at.desc(), RankCheck.id.desc()
        ).limit(limit + 1)
        items = list((await self.session.scalars(statement)).all())
        return items[:limit], len(items) > limit

    async def latest_for_project(
        self, project_id: UUID, user_id: UUID
    ) -> list[RankCheck]:
        numbered = (
            select(
                RankCheck.id.label("id"),
                func.row_number()
                .over(
                    partition_by=RankCheck.keyword_id,
                    order_by=(RankCheck.created_at.desc(), RankCheck.id.desc()),
                )
                .label("row_number"),
            )
            .where(
                RankCheck.project_id == project_id,
                RankCheck.user_id == user_id,
            )
            .subquery()
        )
        statement = (
            select(RankCheck)
            .join(numbered, numbered.c.id == RankCheck.id)
            .where(numbered.c.row_number == 1)
        )
        return list((await self.session.scalars(statement)).all())

    async def has_for_project(self, project_id: UUID, user_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(RankCheck.id)
                .where(
                    RankCheck.project_id == project_id,
                    RankCheck.user_id == user_id,
                )
                .limit(1)
            )
        )

    async def has_for_keyword(
        self, keyword_id: UUID, project_id: UUID, user_id: UUID
    ) -> bool:
        return bool(
            await self.session.scalar(
                select(RankCheck.id)
                .where(
                    RankCheck.keyword_id == keyword_id,
                    RankCheck.project_id == project_id,
                    RankCheck.user_id == user_id,
                )
                .limit(1)
            )
        )

    async def mark_succeeded(
        self,
        check: RankCheck,
        *,
        provider: str,
        provider_request_id: str | None,
        provider_metadata: dict[str, object],
        provider_request_count: int,
        completed_at: datetime,
    ) -> None:
        check.status = RankCheckStatus.SUCCEEDED
        check.provider = provider
        check.provider_request_id = provider_request_id
        check.provider_metadata = provider_metadata
        check.provider_request_count = provider_request_count
        check.completed_at = completed_at
        check.error_code = None
        check.error_message = None
        await self.session.flush()

    async def mark_failed(
        self,
        check: RankCheck,
        *,
        provider: str | None,
        code: str,
        message: str,
        provider_request_count: int,
        completed_at: datetime,
    ) -> None:
        check.status = RankCheckStatus.FAILED
        if provider is not None:
            check.provider = provider
        check.provider_request_count = provider_request_count
        check.completed_at = completed_at
        check.error_code = code
        check.error_message = message
        await self.session.flush()
