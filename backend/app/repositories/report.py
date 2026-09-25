from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.models.keyword_organization import (
    KeywordGroup,
    KeywordTag,
    KeywordTagAssignment,
)
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.ranking import Ranking
from app.models.report import GeneratedReport, ReportDeliveryAttempt, ReportSchedule
from app.models.tracked_site import TrackedSite, TrackedSiteStatus
from app.repositories.analytics import AnalyticsRepository, ExplorerQuery


@dataclass(frozen=True)
class ReportHistoryRow:
    keyword_id: UUID
    keyword: str
    tracked_site_id: UUID
    tracked_site_name: str
    checked_at: datetime
    position: int | None
    checked_depth: int
    rank_check_id: UUID


@dataclass(frozen=True)
class ReportAggregate:
    keyword_site_pairs: int
    distinct_keywords: int
    distinct_tracked_sites: int
    observed_pairs: int
    latest_successful_check_at: datetime | None
    top_3: int
    positions_4_10: int
    positions_11_20: int
    positions_21_50: int
    positions_51_100: int
    not_found_in_depth: int


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        report_id: UUID,
        project_id: UUID,
        user_id: UUID,
        *,
        lock: bool = False,
    ) -> GeneratedReport | None:
        statement = select(GeneratedReport).where(
            GeneratedReport.id == report_id,
            GeneratedReport.project_id == project_id,
            GeneratedReport.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        return cast(GeneratedReport | None, await self.session.scalar(statement))

    async def locked(self, report_id: UUID) -> GeneratedReport | None:
        return cast(
            GeneratedReport | None,
            await self.session.scalar(
                select(GeneratedReport)
                .where(GeneratedReport.id == report_id)
                .with_for_update()
            ),
        )

    async def by_idempotency(
        self, project_id: UUID, user_id: UUID, key: str
    ) -> GeneratedReport | None:
        return cast(
            GeneratedReport | None,
            await self.session.scalar(
                select(GeneratedReport).where(
                    GeneratedReport.project_id == project_id,
                    GeneratedReport.user_id == user_id,
                    GeneratedReport.idempotency_key == key,
                )
            ),
        )

    async def active_count(self, user_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(GeneratedReport.id)).where(
                    GeneratedReport.user_id == user_id,
                    GeneratedReport.status.in_(["pending", "queued", "running"]),
                )
            )
            or 0
        )

    async def recent(
        self,
        project_id: UUID,
        user_id: UUID,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> tuple[list[GeneratedReport], bool]:
        statement = select(GeneratedReport).where(
            GeneratedReport.project_id == project_id,
            GeneratedReport.user_id == user_id,
        )
        if cursor:
            created_at, item_id = cursor
            statement = statement.where(
                or_(
                    GeneratedReport.created_at < created_at,
                    and_(
                        GeneratedReport.created_at == created_at,
                        GeneratedReport.id < item_id,
                    ),
                )
            )
        rows = list(
            await self.session.scalars(
                statement.order_by(
                    GeneratedReport.created_at.desc(), GeneratedReport.id.desc()
                ).limit(limit + 1)
            )
        )
        return rows[:limit], len(rows) > limit

    async def keyword_metadata(
        self, project_id: UUID, keyword_ids: set[UUID]
    ) -> dict[UUID, tuple[str | None, list[str]]]:
        if not keyword_ids:
            return {}
        group_rows = (
            await self.session.execute(
                select(Keyword.id, KeywordGroup.name)
                .outerjoin(
                    KeywordGroup,
                    and_(
                        KeywordGroup.id == Keyword.keyword_group_id,
                        KeywordGroup.project_id == project_id,
                    ),
                )
                .where(Keyword.project_id == project_id, Keyword.id.in_(keyword_ids))
            )
        ).all()
        tag_rows = (
            await self.session.execute(
                select(KeywordTagAssignment.keyword_id, KeywordTag.name)
                .join(
                    KeywordTag,
                    and_(
                        KeywordTag.id == KeywordTagAssignment.tag_id,
                        KeywordTag.project_id == project_id,
                    ),
                )
                .where(
                    KeywordTagAssignment.project_id == project_id,
                    KeywordTagAssignment.keyword_id.in_(keyword_ids),
                )
                .order_by(
                    KeywordTagAssignment.keyword_id,
                    KeywordTag.normalized_name,
                    KeywordTag.id,
                )
            )
        ).all()
        result: dict[UUID, tuple[str | None, list[str]]] = {
            keyword_id: (group, []) for keyword_id, group in group_rows
        }
        for keyword_id, tag in tag_rows:
            result.setdefault(keyword_id, (None, []))[1].append(tag)
        return result

    async def aggregate(self, query: ExplorerQuery) -> ReportAggregate:
        rows, _, _ = AnalyticsRepository(self.session)._filtered_explorer(query)
        current = rows.c.current_position
        value = (
            await self.session.execute(
                select(
                    func.count().label("keyword_site_pairs"),
                    func.count(func.distinct(rows.c.keyword_id)).label(
                        "distinct_keywords"
                    ),
                    func.count(func.distinct(rows.c.tracked_site_id)).label(
                        "distinct_tracked_sites"
                    ),
                    func.count()
                    .filter(rows.c.current_check_id.is_not(None))
                    .label("observed_pairs"),
                    func.max(rows.c.current_checked_at).label(
                        "latest_successful_check_at"
                    ),
                    func.sum(case((current.between(1, 3), 1), else_=0)).label("top_3"),
                    func.sum(case((current.between(4, 10), 1), else_=0)).label(
                        "positions_4_10"
                    ),
                    func.sum(case((current.between(11, 20), 1), else_=0)).label(
                        "positions_11_20"
                    ),
                    func.sum(case((current.between(21, 50), 1), else_=0)).label(
                        "positions_21_50"
                    ),
                    func.sum(case((current.between(51, 100), 1), else_=0)).label(
                        "positions_51_100"
                    ),
                    func.sum(
                        case(
                            (
                                and_(
                                    rows.c.current_check_id.is_not(None),
                                    current.is_(None),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("not_found_in_depth"),
                ).select_from(rows)
            )
        ).one()
        values = dict(value._mapping)
        for key, item in values.items():
            if key != "latest_successful_check_at" and item is None:
                values[key] = 0
        return ReportAggregate(**values)

    async def history_rows(
        self,
        query: ExplorerQuery,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[ReportHistoryRow]:
        checked_at = func.coalesce(RankCheck.completed_at, RankCheck.requested_at)
        organization_filters = AnalyticsRepository._organization_filters(
            query.project_id,
            query.group_filter,
            query.tag_ids,
            query.tag_match,
        )
        statement = (
            select(
                Keyword.id.label("keyword_id"),
                Keyword.keyword,
                TrackedSite.id.label("tracked_site_id"),
                TrackedSite.name.label("tracked_site_name"),
                checked_at.label("checked_at"),
                Ranking.position,
                RankCheck.result_limit.label("checked_depth"),
                RankCheck.id.label("rank_check_id"),
            )
            .select_from(Keyword)
            .join(TrackedSite, true())
            .join(
                RankCheck,
                and_(
                    RankCheck.keyword_id == Keyword.id,
                    RankCheck.project_id == query.project_id,
                    RankCheck.user_id == query.user_id,
                    RankCheck.device_snapshot == query.device,
                    RankCheck.status == RankCheckStatus.SUCCEEDED,
                    checked_at >= TrackedSite.created_at,
                ),
            )
            .outerjoin(
                Ranking,
                and_(
                    Ranking.rank_check_id == RankCheck.id,
                    Ranking.tracked_site_id == TrackedSite.id,
                ),
            )
            .where(
                Keyword.project_id == query.project_id,
                Keyword.active.is_(True),
                TrackedSite.user_id == query.user_id,
                TrackedSite.status == TrackedSiteStatus.ACTIVE,
                checked_at >= start,
                checked_at < end,
                *organization_filters,
            )
        )
        if query.tracked_site_id:
            statement = statement.where(TrackedSite.id == query.tracked_site_id)
        values = (
            await self.session.execute(
                statement.order_by(
                    checked_at,
                    Keyword.keyword_normalized,
                    Keyword.id,
                    TrackedSite.id,
                    RankCheck.id,
                ).limit(limit)
            )
        ).all()
        return [ReportHistoryRow(**row._mapping) for row in values]

    async def schedules(self, project_id: UUID, user_id: UUID) -> list[ReportSchedule]:
        return list(
            await self.session.scalars(
                select(ReportSchedule)
                .where(
                    ReportSchedule.project_id == project_id,
                    ReportSchedule.user_id == user_id,
                )
                .order_by(ReportSchedule.created_at, ReportSchedule.id)
            )
        )

    async def schedule(
        self,
        schedule_id: UUID,
        project_id: UUID,
        user_id: UUID,
        *,
        lock: bool = False,
    ) -> ReportSchedule | None:
        statement = select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.project_id == project_id,
            ReportSchedule.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        return cast(ReportSchedule | None, await self.session.scalar(statement))

    async def active_schedule_count(self, project_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(ReportSchedule.id)).where(
                    ReportSchedule.project_id == project_id,
                    ReportSchedule.active.is_(True),
                )
            )
            or 0
        )

    async def due_schedules(self, now: datetime, limit: int) -> list[ReportSchedule]:
        return list(
            await self.session.scalars(
                select(ReportSchedule)
                .where(
                    ReportSchedule.active.is_(True),
                    ReportSchedule.next_run_at_utc <= now,
                )
                .order_by(ReportSchedule.next_run_at_utc, ReportSchedule.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )

    async def attempts(self, report_id: UUID) -> list[ReportDeliveryAttempt]:
        return list(
            await self.session.scalars(
                select(ReportDeliveryAttempt)
                .where(ReportDeliveryAttempt.generated_report_id == report_id)
                .order_by(
                    ReportDeliveryAttempt.attempt_number,
                    ReportDeliveryAttempt.id,
                )
            )
        )
