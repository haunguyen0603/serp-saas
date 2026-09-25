from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import String, and_, case, func, literal, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import CTE

from app.models.keyword import Keyword
from app.models.keyword_organization import KeywordTagAssignment
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.ranking import Ranking
from app.models.tracked_site import TrackedSite, TrackedSiteStatus


@dataclass(frozen=True)
class KeywordObservationPair:
    keyword_id: UUID
    current_position: int | None
    current_depth: int
    previous_position: int | None
    has_previous: bool
    previous_before_boundary: bool


@dataclass(frozen=True)
class MoverRow:
    keyword_id: UUID
    keyword: str
    tracked_site_id: UUID
    tracked_site_name: str
    previous_position: int
    current_position: int
    change: int


@dataclass(frozen=True)
class HistoryRow:
    checked_at: datetime
    position: int | None
    checked_depth: int
    rank_check_id: UUID


@dataclass(frozen=True)
class ExplorerRow:
    keyword_id: UUID
    keyword: str
    keyword_status: str
    tracked_site_id: UUID
    tracked_site_name: str
    current_check_id: UUID | None
    current_checked_at: datetime | None
    current_position: int | None
    current_depth: int | None
    comparison_check_id: UUID | None
    comparison_checked_at: datetime | None
    comparison_position: int | None
    comparison_depth: int | None
    comparison_before_boundary: bool | None
    movement: str
    change: int | None


@dataclass(frozen=True)
class ExplorerCounts:
    total: int
    improved: int
    declined: int
    unchanged: int
    entered_checked_depth: int
    left_checked_depth: int
    no_previous_data: int
    never_checked: int
    earliest_in_range: int


@dataclass(frozen=True)
class ExplorerQuery:
    project_id: UUID
    user_id: UUID
    device: str
    boundary: datetime
    current_before: datetime | None
    comparison_before: datetime | None
    custom_dates: bool
    search: str | None
    movement: str | None
    position_bucket: str | None
    status: str | None
    tracked_site_id: UUID | None
    group_filter: UUID | Literal["none"] | None
    tag_ids: frozenset[UUID]
    tag_match: Literal["any", "all"]
    sort: str
    order: str
    limit: int
    offset: int


class AnalyticsRepository:
    """Bounded SQL queries over successful persisted RankChecks only."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _organization_filters(
        project_id: UUID,
        group_filter: UUID | Literal["none"] | None,
        tag_ids: set[UUID] | frozenset[UUID],
        tag_match: Literal["any", "all"],
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        if group_filter == "none":
            filters.append(Keyword.keyword_group_id.is_(None))
        elif group_filter is not None:
            filters.append(Keyword.keyword_group_id == group_filter)
        if tag_ids:
            matching_tags = (
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
                matching_tags >= 1
                if tag_match == "any"
                else matching_tags == len(tag_ids)
            )
        return filters

    def _successful_checks(
        self,
        project_id: UUID,
        user_id: UUID,
        device: str,
        *,
        group_filter: UUID | Literal["none"] | None = None,
        tag_ids: set[UUID] | frozenset[UUID] = frozenset(),
        tag_match: Literal["any", "all"] = "any",
    ) -> CTE:
        return (
            select(
                RankCheck.id.label("check_id"),
                RankCheck.keyword_id.label("keyword_id"),
                func.coalesce(RankCheck.completed_at, RankCheck.requested_at).label(
                    "checked_at"
                ),
                RankCheck.result_limit.label("result_limit"),
            )
            .join(Keyword, Keyword.id == RankCheck.keyword_id)
            .where(
                RankCheck.project_id == project_id,
                RankCheck.user_id == user_id,
                RankCheck.device_snapshot == device,
                RankCheck.status == RankCheckStatus.SUCCEEDED,
                Keyword.active.is_(True),
                *self._organization_filters(
                    project_id, group_filter, tag_ids, tag_match
                ),
            )
            .cte("successful_checks")
        )

    @staticmethod
    def _current_and_comparison(checks: CTE, boundary: datetime) -> tuple[CTE, CTE]:
        current_numbered = select(
            *checks.c,
            func.row_number()
            .over(
                partition_by=checks.c.keyword_id,
                order_by=(checks.c.checked_at.desc(), checks.c.check_id.desc()),
            )
            .label("row_number"),
        ).cte("current_numbered")
        current = (
            select(
                current_numbered.c.check_id,
                current_numbered.c.keyword_id,
                current_numbered.c.checked_at,
                current_numbered.c.result_limit,
            )
            .where(current_numbered.c.row_number == 1)
            .cte("current_checks")
        )
        comparison_numbered = (
            select(
                checks.c.check_id,
                checks.c.keyword_id,
                checks.c.checked_at,
                checks.c.result_limit,
                (checks.c.checked_at <= boundary).label("before_boundary"),
                func.row_number()
                .over(
                    partition_by=checks.c.keyword_id,
                    order_by=(
                        case((checks.c.checked_at <= boundary, 0), else_=1),
                        case(
                            (checks.c.checked_at <= boundary, checks.c.checked_at)
                        ).desc(),
                        case(
                            (checks.c.checked_at > boundary, checks.c.checked_at)
                        ).asc(),
                        case(
                            (checks.c.checked_at <= boundary, checks.c.check_id)
                        ).desc(),
                        case((checks.c.checked_at > boundary, checks.c.check_id)).asc(),
                    ),
                )
                .label("row_number"),
            )
            .join(current, current.c.keyword_id == checks.c.keyword_id)
            .where(checks.c.check_id != current.c.check_id)
            .cte("comparison_numbered")
        )
        comparison = (
            select(
                comparison_numbered.c.check_id,
                comparison_numbered.c.keyword_id,
                comparison_numbered.c.checked_at,
                comparison_numbered.c.result_limit,
                comparison_numbered.c.before_boundary,
            )
            .where(comparison_numbered.c.row_number == 1)
            .cte("comparison_checks")
        )
        return current, comparison

    async def active_keyword_count(
        self,
        project_id: UUID,
        *,
        group_filter: UUID | Literal["none"] | None = None,
        tag_ids: set[UUID] | frozenset[UUID] = frozenset(),
        tag_match: Literal["any", "all"] = "any",
    ) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Keyword.id)).where(
                    Keyword.project_id == project_id,
                    Keyword.active.is_(True),
                    *self._organization_filters(
                        project_id, group_filter, tag_ids, tag_match
                    ),
                )
            )
            or 0
        )

    async def keyword_observations(
        self,
        project_id: UUID,
        user_id: UUID,
        device: str,
        boundary: datetime,
        *,
        group_filter: UUID | Literal["none"] | None = None,
        tag_ids: set[UUID] | frozenset[UUID] = frozenset(),
        tag_match: Literal["any", "all"] = "any",
    ) -> list[KeywordObservationPair]:
        checks = self._successful_checks(
            project_id,
            user_id,
            device,
            group_filter=group_filter,
            tag_ids=tag_ids,
            tag_match=tag_match,
        )
        current, comparison = self._current_and_comparison(checks, boundary)
        active_site_ids = select(TrackedSite.id).where(
            TrackedSite.user_id == user_id,
            TrackedSite.status == TrackedSiteStatus.ACTIVE,
        )
        current_position = (
            select(func.min(Ranking.position))
            .where(
                Ranking.rank_check_id == current.c.check_id,
                Ranking.tracked_site_id.in_(active_site_ids),
            )
            .correlate(current)
            .scalar_subquery()
        )
        previous_position = (
            select(func.min(Ranking.position))
            .where(
                Ranking.rank_check_id == comparison.c.check_id,
                Ranking.tracked_site_id.in_(active_site_ids),
            )
            .correlate(comparison)
            .scalar_subquery()
        )
        statement = (
            select(
                current.c.keyword_id,
                current_position.label("current_position"),
                current.c.result_limit,
                previous_position.label("previous_position"),
                comparison.c.check_id.label("previous_check_id"),
                comparison.c.before_boundary,
            )
            .outerjoin(comparison, comparison.c.keyword_id == current.c.keyword_id)
            .order_by(current.c.keyword_id)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            KeywordObservationPair(
                keyword_id=row.keyword_id,
                current_position=row.current_position,
                current_depth=row.result_limit,
                previous_position=row.previous_position,
                has_previous=row.previous_check_id is not None,
                previous_before_boundary=bool(row.before_boundary),
            )
            for row in rows
        ]

    async def movers(
        self,
        project_id: UUID,
        user_id: UUID,
        device: str,
        boundary: datetime,
        *,
        winner: bool,
        limit: int,
    ) -> list[MoverRow]:
        checks = self._successful_checks(project_id, user_id, device)
        current, comparison = self._current_and_comparison(checks, boundary)
        current_ranking = Ranking.__table__.alias("current_ranking")
        previous_ranking = Ranking.__table__.alias("previous_ranking")
        movement = (previous_ranking.c.position - current_ranking.c.position).label(
            "change"
        )
        statement = (
            select(
                current.c.keyword_id,
                Keyword.keyword,
                TrackedSite.id.label("tracked_site_id"),
                TrackedSite.name.label("tracked_site_name"),
                previous_ranking.c.position.label("previous_position"),
                current_ranking.c.position.label("current_position"),
                movement,
            )
            .join(comparison, comparison.c.keyword_id == current.c.keyword_id)
            .join(
                current_ranking,
                current_ranking.c.rank_check_id == current.c.check_id,
            )
            .join(
                previous_ranking,
                and_(
                    previous_ranking.c.rank_check_id == comparison.c.check_id,
                    previous_ranking.c.tracked_site_id
                    == current_ranking.c.tracked_site_id,
                ),
            )
            .join(Keyword, Keyword.id == current.c.keyword_id)
            .join(
                TrackedSite,
                and_(
                    TrackedSite.id == current_ranking.c.tracked_site_id,
                    TrackedSite.user_id == user_id,
                    TrackedSite.status == TrackedSiteStatus.ACTIVE,
                ),
            )
            .where(movement > 0 if winner else movement < 0)
            .order_by(
                movement.desc() if winner else movement.asc(),
                Keyword.keyword,
                Keyword.id,
                TrackedSite.id,
            )
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            MoverRow(
                keyword_id=row.keyword_id,
                keyword=row.keyword,
                tracked_site_id=row.tracked_site_id,
                tracked_site_name=row.tracked_site_name,
                previous_position=row.previous_position,
                current_position=row.current_position,
                change=row.change,
            )
            for row in rows
        ]

    async def keyword_history(
        self,
        project_id: UUID,
        keyword_id: UUID,
        user_id: UUID,
        tracked_site_id: UUID,
        device: str,
        start: datetime,
    ) -> list[HistoryRow]:
        checked_at = func.coalesce(RankCheck.completed_at, RankCheck.requested_at)
        position = (
            select(func.min(Ranking.position))
            .where(
                Ranking.rank_check_id == RankCheck.id,
                Ranking.tracked_site_id == tracked_site_id,
            )
            .correlate(RankCheck)
            .scalar_subquery()
        )
        numbered = (
            select(
                RankCheck.id.label("rank_check_id"),
                checked_at.label("checked_at"),
                RankCheck.result_limit.label("checked_depth"),
                position.label("position"),
                func.row_number()
                .over(
                    partition_by=func.date_trunc(
                        "day", func.timezone("UTC", checked_at)
                    ),
                    order_by=(checked_at.desc(), RankCheck.id.desc()),
                )
                .label("row_number"),
            )
            .where(
                RankCheck.project_id == project_id,
                RankCheck.keyword_id == keyword_id,
                RankCheck.user_id == user_id,
                RankCheck.device_snapshot == device,
                RankCheck.status == RankCheckStatus.SUCCEEDED,
                checked_at >= start,
            )
            .cte("daily_history")
        )
        rows = (
            await self.session.execute(
                select(
                    numbered.c.checked_at,
                    numbered.c.position,
                    numbered.c.checked_depth,
                    numbered.c.rank_check_id,
                )
                .where(numbered.c.row_number == 1)
                .order_by(numbered.c.checked_at, numbered.c.rank_check_id)
            )
        ).all()
        return [
            HistoryRow(
                checked_at=row.checked_at,
                position=row.position,
                checked_depth=row.checked_depth,
                rank_check_id=row.rank_check_id,
            )
            for row in rows
        ]

    def _explorer_comparison(self, query: ExplorerQuery) -> CTE:
        pairs_statement = (
            select(
                Keyword.id.label("keyword_id"),
                Keyword.keyword.label("keyword"),
                Keyword.keyword_normalized.label("keyword_normalized"),
                Keyword.active.label("keyword_active"),
                TrackedSite.id.label("tracked_site_id"),
                TrackedSite.name.label("tracked_site_name"),
                TrackedSite.created_at.label("tracked_site_created_at"),
            )
            .select_from(Keyword)
            .join(TrackedSite, true())
            .where(
                Keyword.project_id == query.project_id,
                Keyword.active.is_(True),
                TrackedSite.user_id == query.user_id,
                TrackedSite.status == TrackedSiteStatus.ACTIVE,
                *self._organization_filters(
                    query.project_id,
                    query.group_filter,
                    query.tag_ids,
                    query.tag_match,
                ),
            )
        )
        if query.search:
            pairs_statement = pairs_statement.where(
                Keyword.keyword.icontains(query.search, autoescape=True)
            )
        if query.tracked_site_id:
            pairs_statement = pairs_statement.where(
                TrackedSite.id == query.tracked_site_id
            )
        pairs = pairs_statement.cte("explorer_pairs")
        checked_at = func.coalesce(RankCheck.completed_at, RankCheck.requested_at)
        observations_statement = (
            select(
                *pairs.c,
                RankCheck.id.label("check_id"),
                checked_at.label("checked_at"),
                RankCheck.result_limit.label("depth"),
                Ranking.position.label("position"),
            )
            .select_from(pairs)
            .join(
                RankCheck,
                and_(
                    RankCheck.keyword_id == pairs.c.keyword_id,
                    RankCheck.project_id == query.project_id,
                    RankCheck.user_id == query.user_id,
                    RankCheck.device_snapshot == query.device,
                    RankCheck.status == RankCheckStatus.SUCCEEDED,
                    checked_at >= pairs.c.tracked_site_created_at,
                ),
            )
            .outerjoin(
                Ranking,
                and_(
                    Ranking.rank_check_id == RankCheck.id,
                    Ranking.tracked_site_id == pairs.c.tracked_site_id,
                ),
            )
        )
        observations = observations_statement.cte("explorer_observations")
        current_source = select(*observations.c)
        if query.current_before is not None:
            current_source = current_source.where(
                observations.c.checked_at < query.current_before
            )
        current_candidates = current_source.subquery("explorer_current_candidates")
        current_numbered = select(
            *current_candidates.c,
            func.row_number()
            .over(
                partition_by=(
                    current_candidates.c.keyword_id,
                    current_candidates.c.tracked_site_id,
                ),
                order_by=(
                    current_candidates.c.checked_at.desc(),
                    current_candidates.c.check_id.desc(),
                ),
            )
            .label("row_number"),
        ).cte("explorer_current_numbered")
        current = (
            select(*current_numbered.c)
            .where(current_numbered.c.row_number == 1)
            .cte("explorer_current")
        )
        if query.custom_dates:
            assert query.comparison_before is not None
            previous_numbered = (
                select(
                    *observations.c,
                    literal(True).label("before_boundary"),
                    func.row_number()
                    .over(
                        partition_by=(
                            observations.c.keyword_id,
                            observations.c.tracked_site_id,
                        ),
                        order_by=(
                            observations.c.checked_at.desc(),
                            observations.c.check_id.desc(),
                        ),
                    )
                    .label("previous_row_number"),
                )
                .where(observations.c.checked_at < query.comparison_before)
                .cte("explorer_previous_numbered")
            )
        else:
            previous_numbered = (
                select(
                    *observations.c,
                    (observations.c.checked_at <= query.boundary).label(
                        "before_boundary"
                    ),
                    func.row_number()
                    .over(
                        partition_by=(
                            observations.c.keyword_id,
                            observations.c.tracked_site_id,
                        ),
                        order_by=(
                            case(
                                (observations.c.checked_at <= query.boundary, 0),
                                else_=1,
                            ),
                            case(
                                (
                                    observations.c.checked_at <= query.boundary,
                                    observations.c.checked_at,
                                )
                            ).desc(),
                            case(
                                (
                                    observations.c.checked_at > query.boundary,
                                    observations.c.checked_at,
                                )
                            ).asc(),
                            observations.c.check_id,
                        ),
                    )
                    .label("previous_row_number"),
                )
                .join(
                    current,
                    and_(
                        current.c.keyword_id == observations.c.keyword_id,
                        current.c.tracked_site_id == observations.c.tracked_site_id,
                    ),
                )
                .where(observations.c.check_id != current.c.check_id)
                .cte("explorer_previous_numbered")
            )
        previous = (
            select(*previous_numbered.c)
            .where(previous_numbered.c.previous_row_number == 1)
            .cte("explorer_previous")
        )
        rows = (
            select(
                pairs.c.keyword_id,
                pairs.c.keyword,
                pairs.c.keyword_normalized,
                pairs.c.keyword_active,
                pairs.c.tracked_site_id,
                pairs.c.tracked_site_name,
                current.c.check_id.label("current_check_id"),
                current.c.checked_at.label("current_checked_at"),
                current.c.position.label("current_position"),
                current.c.depth.label("current_depth"),
                previous.c.check_id.label("comparison_check_id"),
                previous.c.checked_at.label("comparison_checked_at"),
                previous.c.position.label("comparison_position"),
                previous.c.depth.label("comparison_depth"),
                previous.c.before_boundary.label("comparison_before_boundary"),
            )
            .select_from(pairs)
            .outerjoin(
                current,
                and_(
                    current.c.keyword_id == pairs.c.keyword_id,
                    current.c.tracked_site_id == pairs.c.tracked_site_id,
                ),
            )
            .outerjoin(
                previous,
                and_(
                    previous.c.keyword_id == pairs.c.keyword_id,
                    previous.c.tracked_site_id == pairs.c.tracked_site_id,
                ),
            )
            .cte("explorer_comparison")
        )
        return rows

    @staticmethod
    def _explorer_values(
        rows: CTE,
    ) -> tuple[ColumnElement[Any], ColumnElement[Any], ColumnElement[Any]]:
        movement = case(
            (rows.c.current_check_id.is_(None), "never_checked"),
            (rows.c.comparison_check_id.is_(None), "no_previous_data"),
            (
                and_(
                    rows.c.comparison_position.is_(None),
                    rows.c.current_position.is_not(None),
                ),
                "entered_checked_depth",
            ),
            (
                and_(
                    rows.c.comparison_position.is_not(None),
                    rows.c.current_position.is_(None),
                ),
                "left_checked_depth",
            ),
            (
                and_(
                    rows.c.comparison_position.is_(None),
                    rows.c.current_position.is_(None),
                ),
                "unchanged",
            ),
            (rows.c.comparison_position > rows.c.current_position, "improved"),
            (rows.c.comparison_position < rows.c.current_position, "declined"),
            else_="unchanged",
        ).cast(String)
        current_status = case(
            (rows.c.current_check_id.is_(None), "never_checked"),
            (rows.c.current_position.is_(None), "not_found_in_depth"),
            else_="ranked",
        ).cast(String)
        change = case(
            (
                and_(
                    rows.c.current_position.is_not(None),
                    rows.c.comparison_position.is_not(None),
                ),
                rows.c.comparison_position - rows.c.current_position,
            )
        )
        return movement, current_status, change

    def _filtered_explorer(
        self, query: ExplorerQuery
    ) -> tuple[CTE, ColumnElement[Any], ColumnElement[Any]]:
        rows = self._explorer_comparison(query)
        movement, current_status, change = self._explorer_values(rows)
        statement = select(
            *rows.c,
            movement.label("movement"),
            current_status.label("current_status"),
            change.label("change"),
        )
        if query.movement:
            statement = statement.where(movement == query.movement)
        if query.status:
            statement = statement.where(current_status == query.status)
        if query.position_bucket == "top_3":
            statement = statement.where(rows.c.current_position.between(1, 3))
        elif query.position_bucket == "positions_4_10":
            statement = statement.where(rows.c.current_position.between(4, 10))
        elif query.position_bucket == "positions_11_20":
            statement = statement.where(rows.c.current_position.between(11, 20))
        elif query.position_bucket == "positions_21_50":
            statement = statement.where(rows.c.current_position.between(21, 50))
        elif query.position_bucket == "positions_51_100":
            statement = statement.where(rows.c.current_position.between(51, 100))
        elif query.position_bucket == "not_found_in_depth":
            statement = statement.where(
                rows.c.current_check_id.is_not(None),
                rows.c.current_position.is_(None),
            )
        return statement.cte("filtered_explorer"), movement, change

    async def explorer_depth(self, query: ExplorerQuery) -> int:
        checked_at = func.coalesce(RankCheck.completed_at, RankCheck.requested_at)
        statement = (
            select(func.min(RankCheck.result_limit))
            .select_from(RankCheck)
            .join(Keyword, Keyword.id == RankCheck.keyword_id)
            .join(
                TrackedSite,
                and_(
                    TrackedSite.user_id == query.user_id,
                    TrackedSite.status == TrackedSiteStatus.ACTIVE,
                    checked_at >= TrackedSite.created_at,
                ),
            )
            .where(
                RankCheck.project_id == query.project_id,
                RankCheck.user_id == query.user_id,
                RankCheck.device_snapshot == query.device,
                RankCheck.status == RankCheckStatus.SUCCEEDED,
                Keyword.active.is_(True),
                *self._organization_filters(
                    query.project_id,
                    query.group_filter,
                    query.tag_ids,
                    query.tag_match,
                ),
            )
        )
        if query.search:
            statement = statement.where(
                Keyword.keyword.icontains(query.search, autoescape=True)
            )
        if query.tracked_site_id:
            statement = statement.where(TrackedSite.id == query.tracked_site_id)
        if query.current_before is not None:
            statement = statement.where(checked_at < query.current_before)
        return int(await self.session.scalar(statement) or 10)

    async def explorer_counts(self, query: ExplorerQuery) -> ExplorerCounts:
        filtered, _, _ = self._filtered_explorer(query)
        movement = filtered.c.movement
        row = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count().filter(movement == "improved").label("improved"),
                    func.count().filter(movement == "declined").label("declined"),
                    func.count().filter(movement == "unchanged").label("unchanged"),
                    func.count()
                    .filter(movement == "entered_checked_depth")
                    .label("entered_checked_depth"),
                    func.count()
                    .filter(movement == "left_checked_depth")
                    .label("left_checked_depth"),
                    func.count()
                    .filter(movement == "no_previous_data")
                    .label("no_previous_data"),
                    func.count()
                    .filter(movement == "never_checked")
                    .label("never_checked"),
                    func.count()
                    .filter(filtered.c.comparison_before_boundary.is_(False))
                    .label("earliest_in_range"),
                ).select_from(filtered)
            )
        ).one()
        return ExplorerCounts(**row._mapping)

    async def explorer_page(self, query: ExplorerQuery) -> list[ExplorerRow]:
        filtered, _, _ = self._filtered_explorer(query)
        descending = query.order == "desc"
        order_by: list[ColumnElement[Any]]
        if query.sort == "keyword":
            primary = (
                filtered.c.keyword_normalized.desc()
                if descending
                else filtered.c.keyword_normalized.asc()
            )
            order_by = [primary]
        elif query.sort in {"current_position", "comparison_position"}:
            column = getattr(filtered.c, query.sort)
            order_by = [
                case((column.is_(None), 1), else_=0),
                column.desc() if descending else column.asc(),
            ]
        else:
            order_by = [
                case((filtered.c.change.is_(None), 1), else_=0),
                (filtered.c.change.desc() if descending else filtered.c.change.asc()),
                filtered.c.movement,
            ]
        statement = (
            select(filtered)
            .order_by(
                *order_by,
                filtered.c.keyword_normalized,
                filtered.c.keyword_id,
                filtered.c.tracked_site_id,
            )
            .offset(query.offset)
            .limit(query.limit)
        )
        values = (await self.session.execute(statement)).all()
        return [
            ExplorerRow(
                keyword_id=row.keyword_id,
                keyword=row.keyword,
                keyword_status="active" if row.keyword_active else "paused",
                tracked_site_id=row.tracked_site_id,
                tracked_site_name=row.tracked_site_name,
                current_check_id=row.current_check_id,
                current_checked_at=row.current_checked_at,
                current_position=row.current_position,
                current_depth=row.current_depth,
                comparison_check_id=row.comparison_check_id,
                comparison_checked_at=row.comparison_checked_at,
                comparison_position=row.comparison_position,
                comparison_depth=row.comparison_depth,
                comparison_before_boundary=row.comparison_before_boundary,
                movement=row.movement,
                change=row.change,
            )
            for row in values
        ]
