from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    and_,
    case,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.models.keyword_organization import KeywordTagAssignment
from app.models.project_competitor_site import ProjectCompetitorSite, ProjectSiteRole
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_result import RankCheckResult
from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite


@dataclass(frozen=True, slots=True)
class SelectedSiteRow:
    association: ProjectCompetitorSite
    site: TrackedSite
    primary_domain: str | None


@dataclass(frozen=True, slots=True)
class CompetitorSnapshotRow:
    check_id: UUID
    keyword_id: UUID
    keyword: str
    checked_at: datetime
    depth: int
    result_count: int
    max_position: int | None
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None

    @property
    def complete(self) -> bool:
        return (
            self.result_count >= self.depth
            and self.max_position is not None
            and self.max_position >= self.depth
        )


@dataclass(frozen=True, slots=True)
class MatchCandidateRow:
    check_id: UUID
    result_id: UUID
    tracked_site_id: UUID
    tracked_domain_id: UUID
    matched_domain: str
    match_priority: int
    position: int
    url: str
    hostname: str
    title: str | None


class CompetitorSelectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(
        self, project_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> list[SelectedSiteRow]:
        primary_domain = (
            select(TrackedDomain.domain)
            .where(
                TrackedDomain.tracked_site_id == TrackedSite.id,
                TrackedDomain.user_id == user_id,
                TrackedDomain.is_primary.is_(True),
                TrackedDomain.active.is_(True),
            )
            .correlate(TrackedSite)
            .scalar_subquery()
        )
        statement = (
            select(ProjectCompetitorSite, TrackedSite, primary_domain)
            .join(
                TrackedSite,
                and_(
                    TrackedSite.id == ProjectCompetitorSite.tracked_site_id,
                    TrackedSite.user_id == ProjectCompetitorSite.user_id,
                ),
            )
            .where(
                ProjectCompetitorSite.project_id == project_id,
                ProjectCompetitorSite.user_id == user_id,
                ProjectCompetitorSite.archived_at.is_(None),
            )
            .order_by(
                ProjectCompetitorSite.display_order,
                ProjectCompetitorSite.id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=ProjectCompetitorSite)
        rows = (await self.session.execute(statement)).all()
        return [SelectedSiteRow(row[0], row[1], row[2]) for row in rows]

    async def replace(
        self,
        project_id: UUID,
        user_id: UUID,
        primary_site_id: UUID,
        competitor_site_ids: list[UUID],
    ) -> list[SelectedSiteRow]:
        current = await self.list_active(project_id, user_id, for_update=True)
        desired = {
            primary_site_id: (ProjectSiteRole.PRIMARY, 0),
            **{
                site_id: (ProjectSiteRole.COMPETITOR, index)
                for index, site_id in enumerate(competitor_site_ids, start=1)
            },
        }
        now = datetime.now(UTC)
        retained: set[UUID] = set()
        for row in current:
            expected = desired.get(row.site.id)
            if expected is not None and row.association.role == expected[0]:
                row.association.display_order = expected[1]
                retained.add(row.site.id)
                continue
            row.association.archived_at = now
            row.association.updated_at = now
        await self.session.flush()
        self.session.add_all(
            ProjectCompetitorSite(
                project_id=project_id,
                user_id=user_id,
                tracked_site_id=site_id,
                role=role,
                display_order=display_order,
            )
            for site_id, (role, display_order) in desired.items()
            if site_id not in retained
        )
        await self.session.flush()
        return await self.list_active(project_id, user_id)


class CompetitorAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _keyword_filters(
        project_id: UUID,
        group_filter: UUID | Literal["none"] | None,
        tag_ids: frozenset[UUID],
        tag_match: Literal["any", "all"],
        search: str | None,
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = [Keyword.active.is_(True)]
        if search:
            filters.append(Keyword.keyword.icontains(search, autoescape=True))
        if group_filter == "none":
            filters.append(Keyword.keyword_group_id.is_(None))
        elif group_filter is not None:
            filters.append(Keyword.keyword_group_id == group_filter)
        if tag_ids:
            tag_count = (
                select(func.count(func.distinct(KeywordTagAssignment.tag_id)))
                .where(
                    KeywordTagAssignment.project_id == project_id,
                    KeywordTagAssignment.keyword_id == Keyword.id,
                    KeywordTagAssignment.tag_id.in_(tag_ids),
                )
                .correlate(Keyword)
                .scalar_subquery()
            )
            filters.append(
                tag_count >= 1 if tag_match == "any" else tag_count == len(tag_ids)
            )
        return filters

    async def active_keyword_count(
        self,
        project_id: UUID,
        *,
        group_filter: UUID | Literal["none"] | None,
        tag_ids: frozenset[UUID],
        tag_match: Literal["any", "all"],
        search: str | None = None,
    ) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Keyword.id)).where(
                    Keyword.project_id == project_id,
                    *self._keyword_filters(
                        project_id, group_filter, tag_ids, tag_match, search
                    ),
                )
            )
            or 0
        )

    async def snapshots(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        search_engine: str,
        country_code: str,
        language_code: str,
        device: str,
        location: str | None,
        start: datetime,
        end: datetime,
        group_filter: UUID | Literal["none"] | None,
        tag_ids: frozenset[UUID],
        tag_match: Literal["any", "all"],
        search: str | None = None,
        keyword_id: UUID | None = None,
        per_day: bool = False,
    ) -> list[CompetitorSnapshotRow]:
        checked_at = func.coalesce(RankCheck.completed_at, RankCheck.requested_at)
        result_stats = (
            select(
                RankCheckResult.rank_check_id.label("check_id"),
                func.count(RankCheckResult.id).label("result_count"),
                func.max(RankCheckResult.position).label("max_position"),
            )
            .group_by(RankCheckResult.rank_check_id)
            .subquery("competitor_result_stats")
        )
        partition: list[ColumnElement[object]] = [
            cast(ColumnElement[object], Keyword.id)
        ]
        if per_day:
            partition.append(
                cast(ColumnElement[object], func.date_trunc("day", checked_at))
            )
        numbered = (
            select(
                RankCheck.id.label("check_id"),
                Keyword.id.label("keyword_id"),
                Keyword.keyword.label("keyword"),
                checked_at.label("checked_at"),
                RankCheck.result_limit.label("depth"),
                func.coalesce(result_stats.c.result_count, 0).label("result_count"),
                result_stats.c.max_position,
                RankCheck.search_engine_snapshot.label("search_engine"),
                RankCheck.country_code_snapshot.label("country_code"),
                RankCheck.language_code_snapshot.label("language_code"),
                RankCheck.device_snapshot.label("device"),
                RankCheck.location_snapshot.label("location"),
                func.row_number()
                .over(
                    partition_by=partition,
                    order_by=(checked_at.desc(), RankCheck.id.desc()),
                )
                .label("row_number"),
            )
            .join(Keyword, Keyword.id == RankCheck.keyword_id)
            .outerjoin(result_stats, result_stats.c.check_id == RankCheck.id)
            .where(
                RankCheck.project_id == project_id,
                RankCheck.user_id == user_id,
                RankCheck.status == RankCheckStatus.SUCCEEDED,
                RankCheck.search_engine_snapshot == search_engine,
                RankCheck.country_code_snapshot == country_code,
                RankCheck.language_code_snapshot == language_code,
                RankCheck.device_snapshot == device,
                RankCheck.location_snapshot.is_not_distinct_from(location),
                checked_at >= start,
                checked_at <= end,
                *self._keyword_filters(
                    project_id, group_filter, tag_ids, tag_match, search
                ),
                *((RankCheck.keyword_id == keyword_id,) if keyword_id else ()),
            )
            .cte("competitor_snapshot_numbered")
        )
        rows = (
            await self.session.execute(
                select(numbered)
                .where(numbered.c.row_number == 1)
                .order_by(numbered.c.checked_at, numbered.c.keyword_id)
            )
        ).all()
        return [
            CompetitorSnapshotRow(
                check_id=row.check_id,
                keyword_id=row.keyword_id,
                keyword=row.keyword,
                checked_at=row.checked_at,
                depth=row.depth,
                result_count=row.result_count,
                max_position=row.max_position,
                search_engine=row.search_engine,
                country_code=row.country_code,
                language_code=row.language_code,
                device=row.device,
                location=row.location,
            )
            for row in rows
        ]

    async def match_candidates(
        self,
        check_ids: list[UUID],
        site_ids: list[UUID],
        user_id: UUID,
    ) -> list[MatchCandidateRow]:
        if not check_ids or not site_ids:
            return []
        fallback_hostname = case(
            (
                RankCheckResult.hostname.like("www.%"),
                func.substr(RankCheckResult.hostname, 5),
            ),
            else_=literal("www.") + RankCheckResult.hostname,
        )
        rows = (
            await self.session.execute(
                select(
                    RankCheckResult.rank_check_id.label("check_id"),
                    RankCheckResult.id.label("result_id"),
                    TrackedDomain.tracked_site_id,
                    TrackedDomain.id.label("tracked_domain_id"),
                    TrackedDomain.domain.label("matched_domain"),
                    case(
                        (TrackedDomain.domain == RankCheckResult.hostname, 0),
                        else_=1,
                    ).label("match_priority"),
                    RankCheckResult.position,
                    RankCheckResult.url,
                    RankCheckResult.hostname,
                    RankCheckResult.title,
                )
                .join(
                    TrackedDomain,
                    and_(
                        TrackedDomain.user_id == user_id,
                        TrackedDomain.tracked_site_id.in_(site_ids),
                        TrackedDomain.active.is_(True),
                        or_(
                            TrackedDomain.domain == RankCheckResult.hostname,
                            TrackedDomain.domain == fallback_hostname,
                        ),
                    ),
                )
                .where(RankCheckResult.rank_check_id.in_(check_ids))
                .order_by(
                    RankCheckResult.rank_check_id,
                    RankCheckResult.position,
                    RankCheckResult.id,
                    "match_priority",
                    TrackedDomain.tracked_site_id,
                )
            )
        ).all()
        return [MatchCandidateRow(**row._mapping) for row in rows]
