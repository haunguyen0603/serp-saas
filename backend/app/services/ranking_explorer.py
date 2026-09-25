import base64
import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, cast
from uuid import UUID

from app.core.errors import AppError
from app.repositories.analytics import AnalyticsRepository, ExplorerQuery, ExplorerRow
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.schemas.analytics import AnalyticsRange
from app.schemas.ranking_explorer import (
    ExplorerMovement,
    ExplorerMovementValue,
    ExplorerObservation,
    ExplorerPage,
    ExplorerResultsSummary,
    ExplorerTrackedSite,
    RankingExplorerItem,
    RankingExplorerResponse,
)

_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}
_MOVEMENTS = {
    "improved",
    "declined",
    "unchanged",
    "entered_checked_depth",
    "left_checked_depth",
    "no_previous_data",
    "never_checked",
}
_STATUSES = {"ranked", "not_found_in_depth", "never_checked"}
_SORTS = {"keyword", "current_position", "comparison_position", "change"}
_ORDERS = {"asc", "desc"}


def _offset_cursor(offset: int) -> str:
    payload = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def _decode_offset_cursor(value: str | None) -> int:
    if value is None:
        return 0
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding))
        offset = payload["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError
        return offset
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise AppError(422, "INVALID_CURSOR", "Pagination cursor is invalid.") from None


class RankingExplorerService:
    def __init__(
        self,
        analytics: AnalyticsRepository,
        projects: ProjectRepository,
        tracked_sites: TrackedSiteRepository,
        organizations: KeywordOrganizationRepository | None = None,
    ) -> None:
        self.analytics = analytics
        self.projects = projects
        self.tracked_sites = tracked_sites
        self.organizations = organizations

    @staticmethod
    def _parse_date(value: str, field: str) -> date:
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise AppError(
                422, "INVALID_DATE_RANGE", f"{field} must be an ISO date."
            ) from None
        if parsed.isoformat() != value:
            raise AppError(422, "INVALID_DATE_RANGE", f"{field} must be an ISO date.")
        return parsed

    @staticmethod
    def _supported_buckets(depth: int) -> list[str]:
        values = ["top_3"]
        if depth >= 4:
            values.append("positions_4_10")
        if depth >= 11:
            values.append("positions_11_20")
        if depth >= 21:
            values.append("positions_21_50")
        if depth >= 51:
            values.append("positions_51_100")
        values.append("not_found_in_depth")
        return values

    @staticmethod
    def _observation(row: ExplorerRow, *, current: bool) -> ExplorerObservation | None:
        check_id = row.current_check_id if current else row.comparison_check_id
        checked_at = row.current_checked_at if current else row.comparison_checked_at
        position = row.current_position if current else row.comparison_position
        depth = row.current_depth if current else row.comparison_depth
        if check_id is None or checked_at is None or depth is None:
            return None
        return ExplorerObservation(
            checked_at=checked_at,
            position=position,
            status="ranked" if position is not None else "not_found_in_depth",
            depth=depth,
            rank_check_id=check_id,
        )

    async def list(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        q: str | None,
        range_value: str,
        compare_from: str | None,
        compare_to: str | None,
        movement: str | None,
        position_bucket: str | None,
        tracked_site_id: UUID | None,
        status: str | None,
        sort: str,
        order: str,
        limit: int,
        cursor: str | None,
        group_id: str | None = None,
        tag_ids: str | None = None,
        tag_match: str = "any",
    ) -> RankingExplorerResponse:
        project = await self.projects.get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        if movement is not None and movement not in _MOVEMENTS:
            raise AppError(
                422, "INVALID_MOVEMENT_FILTER", "Movement filter is invalid."
            )
        if status is not None and status not in _STATUSES:
            raise AppError(422, "INVALID_STATUS_FILTER", "Status filter is invalid.")
        if sort not in _SORTS:
            raise AppError(422, "INVALID_SORT_FIELD", "Sort field is invalid.")
        if order not in _ORDERS:
            raise AppError(422, "INVALID_SORT_ORDER", "Sort order is invalid.")
        if limit not in {25, 50, 100}:
            raise AppError(422, "VALIDATION_ERROR", "Limit must be 25, 50, or 100.")
        if tracked_site_id is not None and (
            await self.tracked_sites.get_for_user(tracked_site_id, user_id) is None
        ):
            raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
        group_filter: UUID | Literal["none"] | None = None
        if group_id == "none":
            group_filter = "none"
        elif group_id:
            try:
                selected_group = UUID(group_id)
            except ValueError:
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                ) from None
            if (
                self.organizations is None
                or len(
                    await self.organizations.groups_for_project(
                        project_id, {selected_group}
                    )
                )
                != 1
            ):
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                )
            group_filter = selected_group
        if tag_match not in {"any", "all"}:
            raise AppError(422, "INVALID_TAG_MATCH", "Tag match mode is invalid.")
        selected_tags: set[UUID] = set()
        if tag_ids:
            try:
                selected_tags = {UUID(value) for value in tag_ids.split(",") if value}
            except ValueError:
                raise AppError(
                    422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid."
                ) from None
            if not selected_tags or len(selected_tags) > 100:
                raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
            if self.organizations is None or len(
                await self.organizations.tags_for_project(project_id, selected_tags)
            ) != len(selected_tags):
                raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
        custom = compare_from is not None or compare_to is not None
        now = datetime.now(UTC)
        from_value: str | None = None
        to_value: str | None = None
        if custom:
            if compare_from is None or compare_to is None:
                raise AppError(
                    422,
                    "INVALID_DATE_RANGE",
                    "Both compare_from and compare_to are required.",
                )
            from_date = self._parse_date(compare_from, "compare_from")
            to_date = self._parse_date(compare_to, "compare_to")
            if from_date > to_date:
                raise AppError(
                    422,
                    "INVALID_DATE_RANGE",
                    "compare_from must be before or equal to compare_to.",
                )
            current_before = datetime.combine(
                to_date + timedelta(days=1), time.min, UTC
            )
            comparison_before = datetime.combine(
                from_date + timedelta(days=1), time.min, UTC
            )
            boundary = comparison_before
            selected_range: AnalyticsRange | str = "custom"
            from_value = from_date.isoformat()
            to_value = to_date.isoformat()
        else:
            if range_value not in _RANGE_DAYS:
                raise AppError(
                    422,
                    "INVALID_ANALYTICS_RANGE",
                    "Analytics range must be 7d, 30d, or 90d.",
                )
            selected_range = cast(AnalyticsRange, range_value)
            boundary = now - timedelta(days=_RANGE_DAYS[range_value])
            current_before = None
            comparison_before = None
        search = (q or "").strip() or None
        if search and len(search) > 512:
            raise AppError(422, "VALIDATION_ERROR", "Search query is too long.")
        offset = _decode_offset_cursor(cursor)
        base_query = ExplorerQuery(
            project_id=project_id,
            user_id=user_id,
            device=project.device,
            boundary=boundary,
            current_before=current_before,
            comparison_before=comparison_before,
            custom_dates=custom,
            search=search,
            movement=movement,
            position_bucket=position_bucket,
            status=status,
            tracked_site_id=tracked_site_id,
            group_filter=group_filter,
            tag_ids=frozenset(selected_tags),
            tag_match=cast(Literal["any", "all"], tag_match),
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )
        depth = await self.analytics.explorer_depth(base_query)
        supported = self._supported_buckets(depth)
        if position_bucket is not None and position_bucket not in supported:
            raise AppError(
                422,
                "INVALID_POSITION_BUCKET",
                "Position bucket is not supported by the checked depth.",
            )
        counts = await self.analytics.explorer_counts(base_query)
        rows = await self.analytics.explorer_page(base_query)
        next_offset = offset + len(rows)
        next_cursor = (
            _offset_cursor(next_offset) if next_offset < counts.total else None
        )
        if custom:
            basis = "custom_dates"
        elif counts.earliest_in_range:
            basis = "earliest_in_range"
        elif counts.total and counts.total != counts.never_checked:
            basis = "range_boundary"
        else:
            basis = "none"
        return RankingExplorerResponse(
            project_id=project_id,
            device=project.device,
            range=cast(AnalyticsRange | Literal["custom"], selected_range),
            compare_from=from_value,
            compare_to=to_value,
            comparison_basis=cast(
                Literal["range_boundary", "earliest_in_range", "custom_dates", "none"],
                basis,
            ),
            effective_depth=depth,
            supported_position_buckets=supported,
            summary=ExplorerResultsSummary(
                total=counts.total,
                improved=counts.improved,
                declined=counts.declined,
                unchanged=counts.unchanged,
                entered_checked_depth=counts.entered_checked_depth,
                left_checked_depth=counts.left_checked_depth,
                no_previous_data=counts.no_previous_data,
                never_checked=counts.never_checked,
            ),
            page=ExplorerPage(limit=limit, next_cursor=next_cursor),
            items=[
                RankingExplorerItem(
                    keyword_id=row.keyword_id,
                    keyword=row.keyword,
                    keyword_status=cast(
                        Literal["active", "paused"], row.keyword_status
                    ),
                    tracked_site=ExplorerTrackedSite(
                        id=row.tracked_site_id, name=row.tracked_site_name
                    ),
                    device=project.device,
                    comparison=self._observation(row, current=False),
                    current=self._observation(row, current=True),
                    movement=ExplorerMovementValue(
                        type=cast(ExplorerMovement, row.movement), change=row.change
                    ),
                )
                for row in rows
            ],
        )
