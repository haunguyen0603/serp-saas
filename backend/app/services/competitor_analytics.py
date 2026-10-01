import base64
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, TypedDict, cast
from urllib.parse import urlsplit
from uuid import UUID

from app.core.errors import AppError
from app.models.project import Project
from app.models.project_competitor_site import ProjectSiteRole
from app.models.tracked_site import TrackedSiteStatus
from app.repositories.competitor_analytics import (
    CompetitorAnalyticsRepository,
    CompetitorSelectionRepository,
    CompetitorSnapshotRow,
    MatchCandidateRow,
    SelectedSiteRow,
)
from app.repositories.keyword import KeywordRepository
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.schemas.competitor_analytics import (
    CompetitorKeywordListResponse,
    CompetitorKeywordObservationResponse,
    CompetitorKeywordRow,
    CompetitorMatchedResult,
    CompetitorObservationSiteDetail,
    CompetitorOverviewResponse,
    CompetitorSelectedSite,
    CompetitorSelectionResponse,
    CompetitorSelectionUpdate,
    CompetitorSiteMetric,
    CompetitorSiteObservation,
    CompetitorStatus,
    CompetitorTrendPoint,
    CompetitorTrendSitePoint,
    CompetitorTrendsResponse,
    CoverageQuality,
    HeadToHeadMetric,
)

RangeValue = Literal["7d", "30d", "90d", "custom"]
GroupFilter = UUID | Literal["none"] | None
TagMatch = Literal["any", "all"]


class EnvironmentFilter(TypedDict):
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None


_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}
_COMPARISON_STATES = {
    "all",
    "both_ranked",
    "my_site_ahead",
    "competitor_ahead",
    "tied",
}
_SORTS = {
    "keyword",
    "primary_position",
    "competitor_position",
    "position_gap",
    "checked_at",
}


@dataclass(frozen=True, slots=True)
class ResolvedMatch:
    position: int
    url: str
    hostname: str
    title: str | None


@dataclass(frozen=True, slots=True)
class Observation:
    status: str
    position: int | None
    matches: tuple[ResolvedMatch, ...]


def _offset_cursor(offset: int) -> str:
    value = json.dumps({"offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode_cursor(value: str | None) -> int:
    if value is None:
        return 0
    try:
        padded = value + "=" * (-len(value) % 4)
        offset = json.loads(base64.urlsafe_b64decode(padded))["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError
        return offset
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise AppError(422, "INVALID_CURSOR", "Pagination cursor is invalid.") from None


class CompetitorAnalyticsService:
    def __init__(
        self,
        analytics: CompetitorAnalyticsRepository,
        selections: CompetitorSelectionRepository,
        projects: ProjectRepository,
        tracked_sites: TrackedSiteRepository,
        keywords: KeywordRepository,
        organizations: KeywordOrganizationRepository,
    ) -> None:
        self.analytics = analytics
        self.selections = selections
        self.projects = projects
        self.tracked_sites = tracked_sites
        self.keywords = keywords
        self.organizations = organizations

    @staticmethod
    def _selection_response(
        project_id: UUID, rows: list[SelectedSiteRow]
    ) -> CompetitorSelectionResponse:
        sites = [
            CompetitorSelectedSite(
                tracked_site_id=row.site.id,
                name=row.site.name,
                primary_domain=row.primary_domain,
                role=cast(Literal["primary", "competitor"], row.association.role),
            )
            for row in rows
        ]
        return CompetitorSelectionResponse(
            project_id=project_id,
            primary_site=next((site for site in sites if site.role == "primary"), None),
            competitor_sites=[site for site in sites if site.role == "competitor"],
        )

    async def get_selection(
        self, project_id: UUID, user_id: UUID
    ) -> CompetitorSelectionResponse:
        await self._project(project_id, user_id)
        return self._selection_response(
            project_id, await self.selections.list_active(project_id, user_id)
        )

    async def replace_selection(
        self, project_id: UUID, user_id: UUID, data: CompetitorSelectionUpdate
    ) -> CompetitorSelectionResponse:
        await self._project(project_id, user_id)
        site_ids = [data.primary_tracked_site_id, *data.competitor_tracked_site_ids]
        for site_id in site_ids:
            site = await self.tracked_sites.get_for_user(site_id, user_id)
            if site is None:
                raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
            if site.status is not TrackedSiteStatus.ACTIVE:
                raise AppError(
                    422,
                    "TRACKED_SITE_NOT_ACTIVE",
                    "Only active Tracked Sites can be selected.",
                )
        rows = await self.selections.replace(
            project_id,
            user_id,
            data.primary_tracked_site_id,
            data.competitor_tracked_site_ids,
        )
        return self._selection_response(project_id, rows)

    async def overview(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        range_value: str,
        start_date: str | None,
        end_date: str | None,
        group_id: str | None,
        tag_ids: str | None,
        tag_match: str,
    ) -> CompetitorOverviewResponse:
        project = await self._project(project_id, user_id)
        selection, primary, competitors = await self._require_selection(
            project_id, user_id
        )
        selected_range, start, end = self._period(range_value, start_date, end_date)
        group_filter, tags, match_mode = await self._organization_filters(
            project_id, group_id, tag_ids, tag_match
        )
        snapshots = await self.analytics.snapshots(
            project_id,
            user_id,
            **self._environment(project),
            start=start,
            end=end,
            group_filter=group_filter,
            tag_ids=tags,
            tag_match=match_mode,
        )
        cohort = await self.analytics.active_keyword_count(
            project_id,
            group_filter=group_filter,
            tag_ids=tags,
            tag_match=match_mode,
        )
        resolved, ambiguous = await self._resolved(snapshots, selection, user_id)
        top_n = min([10, *(row.depth for row in snapshots)]) if snapshots else 10
        observations = self._observations(snapshots, selection, resolved, ambiguous)
        metrics: list[CompetitorSiteMetric] = []
        for site in selection:
            site_values = [
                observations[(snapshot.check_id, site.site.id)]
                for snapshot in snapshots
            ]
            comparable = sum(
                value.status in {"ranked", "not_found_in_checked_depth"}
                for value in site_values
            )
            top_three = sum(
                value.position is not None and value.position <= 3
                for value in site_values
            )
            top_count = sum(
                value.position is not None and value.position <= top_n
                for value in site_values
            )
            metrics.append(
                CompetitorSiteMetric(
                    tracked_site_id=site.site.id,
                    name=site.site.name,
                    top_3=top_three,
                    top_n=top_count,
                    comparable_keywords=comparable,
                    observed_top_n_coverage_pct=(
                        round(top_count * 100 / comparable, 2) if comparable else 0
                    ),
                    not_found_in_checked_depth=sum(
                        value.status == "not_found_in_checked_depth"
                        for value in site_values
                    ),
                    not_observed=sum(
                        value.status == "not_observed" for value in site_values
                    ),
                    ambiguous_match=sum(
                        value.status == "ambiguous_match" for value in site_values
                    ),
                )
            )
        comparisons = [
            self._head_to_head(
                snapshots,
                observations,
                primary,
                competitor,
                top_n,
            )
            for competitor in competitors
        ]
        partial = sum(
            not snapshot.complete
            or any(
                observations[(snapshot.check_id, site.site.id)].status
                in {"not_observed", "ambiguous_match"}
                for site in selection
            )
            for snapshot in snapshots
        )
        return CompetitorOverviewResponse(
            project_id=project_id,
            device=project.device,
            range=selected_range,
            as_of=end,
            effective_depth=top_n,
            top_n=top_n,
            keyword_cohort=cohort,
            qualifying_keywords=len(snapshots),
            partial_or_unobserved_keywords=partial,
            primary_site=self._site_response(primary),
            sites=metrics,
            comparisons=comparisons,
            coverage_quality=self._quality(snapshots),
            latest_successful_check_at=max(
                (row.checked_at for row in snapshots), default=None
            ),
        )

    async def keywords_page(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        range_value: str,
        start_date: str | None,
        end_date: str | None,
        q: str | None,
        group_id: str | None,
        tag_ids: str | None,
        tag_match: str,
        comparison_state: str,
        opportunity: bool,
        opponent_site_id: UUID | None,
        sort: str,
        order: str,
        limit: int,
        cursor: str | None,
    ) -> CompetitorKeywordListResponse:
        project = await self._project(project_id, user_id)
        selection, primary, competitors = await self._require_selection(
            project_id, user_id
        )
        _, start, end = self._period(range_value, start_date, end_date)
        group_filter, tags, match_mode = await self._organization_filters(
            project_id, group_id, tag_ids, tag_match
        )
        if comparison_state not in _COMPARISON_STATES:
            raise AppError(
                422, "INVALID_COMPARISON_STATE", "Comparison state is invalid."
            )
        if sort not in _SORTS:
            raise AppError(422, "INVALID_SORT_FIELD", "Sort field is invalid.")
        if order not in {"asc", "desc"}:
            raise AppError(422, "INVALID_SORT_ORDER", "Sort order is invalid.")
        if limit not in {25, 50, 100}:
            raise AppError(422, "VALIDATION_ERROR", "Limit must be 25, 50, or 100.")
        opponent = self._opponent(competitors, opponent_site_id)
        search = (q or "").strip() or None
        if search and len(search) > 512:
            raise AppError(422, "VALIDATION_ERROR", "Search query is too long.")
        snapshots = await self.analytics.snapshots(
            project_id,
            user_id,
            **self._environment(project),
            start=start,
            end=end,
            group_filter=group_filter,
            tag_ids=tags,
            tag_match=match_mode,
            search=search,
        )
        resolved, ambiguous = await self._resolved(snapshots, selection, user_id)
        observations = self._observations(snapshots, selection, resolved, ambiguous)
        top_n = min([10, *(row.depth for row in snapshots)]) if snapshots else 10
        rows = [
            self._keyword_row(
                snapshot,
                selection,
                observations,
                primary,
                opponent,
                top_n,
            )
            for snapshot in snapshots
        ]
        if comparison_state == "both_ranked":
            rows = [row for row in rows if row.position_gap is not None]
        elif comparison_state != "all":
            rows = [row for row in rows if row.comparison_state == comparison_state]
        if opportunity:
            rows = [row for row in rows if row.opportunity]

        def sort_key(row: CompetitorKeywordRow) -> tuple[object, ...]:
            primary_value = next(
                site for site in row.sites if site.tracked_site_id == primary.site.id
            )
            opponent_value = next(
                (
                    site
                    for site in row.sites
                    if opponent and site.tracked_site_id == opponent.site.id
                ),
                None,
            )
            selected: int | float | datetime | str | tuple[int, ...] | None
            if sort == "primary_position":
                selected = primary_value.position
            elif sort == "competitor_position":
                selected = opponent_value.position if opponent_value else None
            elif sort == "position_gap":
                selected = row.position_gap
            elif sort == "checked_at":
                selected = row.checked_at
            else:
                selected = row.keyword.casefold()
            if isinstance(selected, int) and order == "desc":
                selected = -selected
            elif isinstance(selected, datetime) and order == "desc":
                selected = -selected.timestamp()
            elif isinstance(selected, str) and order == "desc":
                selected = tuple(-ord(character) for character in selected)
            return (
                selected is None,
                selected if selected is not None else 0,
                row.keyword.casefold(),
                str(row.keyword_id),
            )

        rows.sort(key=sort_key)
        offset = _decode_cursor(cursor)
        page = rows[offset : offset + limit]
        next_offset = offset + len(page)
        has_more = next_offset < len(rows)
        return CompetitorKeywordListResponse(
            project_id=project_id,
            items=page,
            next_cursor=_offset_cursor(next_offset) if has_more else None,
            has_more=has_more,
            total=len(rows),
            top_n=top_n,
            opponent_site_id=opponent.site.id if opponent else None,
        )

    async def trends(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        range_value: str,
        start_date: str | None,
        end_date: str | None,
        group_id: str | None,
        tag_ids: str | None,
        tag_match: str,
    ) -> CompetitorTrendsResponse:
        project = await self._project(project_id, user_id)
        selection, _, _ = await self._require_selection(project_id, user_id)
        selected_range, start, end = self._period(range_value, start_date, end_date)
        group_filter, tags, match_mode = await self._organization_filters(
            project_id, group_id, tag_ids, tag_match
        )
        snapshots = await self.analytics.snapshots(
            project_id,
            user_id,
            **self._environment(project),
            start=start,
            end=end,
            group_filter=group_filter,
            tag_ids=tags,
            tag_match=match_mode,
            per_day=True,
        )
        resolved, ambiguous = await self._resolved(snapshots, selection, user_id)
        observations = self._observations(snapshots, selection, resolved, ambiguous)
        top_n = min([10, *(row.depth for row in snapshots)]) if snapshots else 10
        by_day: dict[date, list[CompetitorSnapshotRow]] = defaultdict(list)
        for snapshot in snapshots:
            by_day[snapshot.checked_at.astimezone(UTC).date()].append(snapshot)
        points: list[CompetitorTrendPoint] = []
        for day, day_rows in sorted(by_day.items()):
            site_points: list[CompetitorTrendSitePoint] = []
            for site in selection:
                values = [
                    observations[(snapshot.check_id, site.site.id)]
                    for snapshot in day_rows
                ]
                comparable = sum(
                    value.status in {"ranked", "not_found_in_checked_depth"}
                    for value in values
                )
                appearances = sum(
                    value.position is not None and value.position <= top_n
                    for value in values
                )
                site_points.append(
                    CompetitorTrendSitePoint(
                        tracked_site_id=site.site.id,
                        name=site.site.name,
                        top_n_appearances=appearances,
                        comparable_keywords=comparable,
                        observed_top_n_coverage_pct=(
                            round(appearances * 100 / comparable, 2)
                            if comparable
                            else 0
                        ),
                        not_observed=sum(
                            value.status in {"not_observed", "ambiguous_match"}
                            for value in values
                        ),
                    )
                )
            points.append(
                CompetitorTrendPoint(
                    date=day,
                    observed_keywords=len(day_rows),
                    coverage_quality=self._quality(day_rows),
                    sites=site_points,
                )
            )
        return CompetitorTrendsResponse(
            project_id=project_id,
            range=selected_range,
            top_n=top_n,
            points=points,
        )

    async def keyword_observation(
        self,
        project_id: UUID,
        keyword_id: UUID,
        user_id: UUID,
        *,
        range_value: str,
        start_date: str | None,
        end_date: str | None,
    ) -> CompetitorKeywordObservationResponse:
        project = await self._project(project_id, user_id)
        if (
            await self.keywords.get_for_user_project(keyword_id, project_id, user_id)
            is None
        ):
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
        selection, _, _ = await self._require_selection(project_id, user_id)
        _, start, end = self._period(range_value, start_date, end_date)
        snapshots = await self.analytics.snapshots(
            project_id,
            user_id,
            **self._environment(project),
            start=start,
            end=end,
            group_filter=None,
            tag_ids=frozenset(),
            tag_match="any",
            keyword_id=keyword_id,
        )
        if not snapshots:
            raise AppError(
                404,
                "COMPETITOR_OBSERVATION_NOT_FOUND",
                "No successful persisted observation exists in this range.",
            )
        snapshot = snapshots[-1]
        resolved, ambiguous = await self._resolved([snapshot], selection, user_id)
        observations = self._observations([snapshot], selection, resolved, ambiguous)
        details: list[CompetitorObservationSiteDetail] = []
        for site in selection:
            value = observations[(snapshot.check_id, site.site.id)]
            details.append(
                CompetitorObservationSiteDetail(
                    **self._observation_response(snapshot, site, value).model_dump(),
                    matched_results=[
                        CompetitorMatchedResult(
                            position=match.position,
                            url=match.url,
                            hostname=match.hostname,
                            title=match.title,
                        )
                        for match in value.matches
                        if self._safe_url(match.url)
                    ],
                )
            )
        return CompetitorKeywordObservationResponse(
            project_id=project_id,
            keyword_id=keyword_id,
            keyword=snapshot.keyword,
            rank_check_id=snapshot.check_id,
            checked_at=snapshot.checked_at,
            search_engine=snapshot.search_engine,
            country_code=snapshot.country_code,
            language_code=snapshot.language_code,
            device=snapshot.device,
            location=snapshot.location,
            checked_depth=snapshot.depth,
            snapshot_complete=snapshot.complete,
            coverage_quality="complete" if snapshot.complete else "partial",
            sites=details,
        )

    async def _project(self, project_id: UUID, user_id: UUID) -> Project:
        project = await self.projects.get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        return project

    @staticmethod
    def _environment(project: Project) -> EnvironmentFilter:
        return {
            "search_engine": project.search_engine,
            "country_code": project.country_code,
            "language_code": project.language_code,
            "device": project.device,
            "location": project.location,
        }

    async def _require_selection(
        self, project_id: UUID, user_id: UUID
    ) -> tuple[list[SelectedSiteRow], SelectedSiteRow, list[SelectedSiteRow]]:
        rows = await self.selections.list_active(project_id, user_id)
        primary = next(
            (row for row in rows if row.association.role == ProjectSiteRole.PRIMARY),
            None,
        )
        if primary is None:
            raise AppError(
                409,
                "COMPETITOR_PRIMARY_SITE_REQUIRED",
                "Select a primary Tracked Site before viewing competitor analytics.",
            )
        competitors = [
            row for row in rows if row.association.role == ProjectSiteRole.COMPETITOR
        ]
        return rows, primary, competitors

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

    def _period(
        self, range_value: str, start_date: str | None, end_date: str | None
    ) -> tuple[RangeValue, datetime, datetime]:
        now = datetime.now(UTC)
        if start_date is not None or end_date is not None:
            if start_date is None or end_date is None:
                raise AppError(
                    422,
                    "INVALID_DATE_RANGE",
                    "Both start_date and end_date are required.",
                )
            start_day = self._parse_date(start_date, "start_date")
            end_day = self._parse_date(end_date, "end_date")
            if start_day > end_day or (end_day - start_day).days > 90:
                raise AppError(
                    422,
                    "INVALID_DATE_RANGE",
                    "The date range must be ordered and at most 90 days.",
                )
            return (
                "custom",
                datetime.combine(start_day, time.min, UTC),
                datetime.combine(end_day + timedelta(days=1), time.min, UTC)
                - timedelta(microseconds=1),
            )
        if range_value not in _RANGE_DAYS:
            raise AppError(
                422,
                "INVALID_ANALYTICS_RANGE",
                "Analytics range must be 7d, 30d, or 90d.",
            )
        return (
            cast(RangeValue, range_value),
            now - timedelta(days=_RANGE_DAYS[range_value]),
            now,
        )

    async def _organization_filters(
        self,
        project_id: UUID,
        group_id: str | None,
        tag_ids: str | None,
        tag_match: str,
    ) -> tuple[GroupFilter, frozenset[UUID], TagMatch]:
        group_filter: GroupFilter = None
        if group_id == "none":
            group_filter = "none"
        elif group_id:
            try:
                parsed_group = UUID(group_id)
            except ValueError:
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                ) from None
            if (
                len(
                    await self.organizations.groups_for_project(
                        project_id, {parsed_group}
                    )
                )
                != 1
            ):
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                )
            group_filter = parsed_group
        if tag_match not in {"any", "all"}:
            raise AppError(422, "INVALID_TAG_MATCH", "Tag match mode is invalid.")
        tags: set[UUID] = set()
        if tag_ids:
            try:
                tags = {UUID(value) for value in tag_ids.split(",") if value}
            except ValueError:
                raise AppError(
                    422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid."
                ) from None
            if (
                not tags
                or len(tags) > 100
                or len(await self.organizations.tags_for_project(project_id, tags))
                != len(tags)
            ):
                raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
        return group_filter, frozenset(tags), cast(TagMatch, tag_match)

    async def _resolved(
        self,
        snapshots: list[CompetitorSnapshotRow],
        selection: list[SelectedSiteRow],
        user_id: UUID,
    ) -> tuple[
        dict[tuple[UUID, UUID], tuple[ResolvedMatch, ...]],
        set[tuple[UUID, UUID]],
    ]:
        candidates = await self.analytics.match_candidates(
            [row.check_id for row in snapshots],
            [row.site.id for row in selection],
            user_id,
        )
        by_result: dict[tuple[UUID, UUID], list[MatchCandidateRow]] = defaultdict(list)
        for candidate in candidates:
            by_result[(candidate.check_id, candidate.result_id)].append(candidate)
        matches: dict[tuple[UUID, UUID], list[ResolvedMatch]] = defaultdict(list)
        ambiguous: set[tuple[UUID, UUID]] = set()
        for result_candidates in by_result.values():
            priority = min(row.match_priority for row in result_candidates)
            preferred = [
                row for row in result_candidates if row.match_priority == priority
            ]
            site_ids = {row.tracked_site_id for row in preferred}
            check_id = preferred[0].check_id
            if len(site_ids) != 1:
                ambiguous.update((check_id, site_id) for site_id in site_ids)
                continue
            winner = preferred[0]
            matches[(check_id, winner.tracked_site_id)].append(
                ResolvedMatch(
                    position=winner.position,
                    url=winner.url,
                    hostname=winner.hostname,
                    title=winner.title,
                )
            )
        return (
            {
                key: tuple(sorted(values, key=lambda value: value.position))
                for key, values in matches.items()
            },
            ambiguous,
        )

    @staticmethod
    def _observations(
        snapshots: list[CompetitorSnapshotRow],
        selection: list[SelectedSiteRow],
        resolved: dict[tuple[UUID, UUID], tuple[ResolvedMatch, ...]],
        ambiguous: set[tuple[UUID, UUID]],
    ) -> dict[tuple[UUID, UUID], Observation]:
        values: dict[tuple[UUID, UUID], Observation] = {}
        for snapshot in snapshots:
            for site in selection:
                key = (snapshot.check_id, site.site.id)
                matches = resolved.get(key, ())
                if matches:
                    values[key] = Observation("ranked", matches[0].position, matches)
                elif key in ambiguous:
                    values[key] = Observation("ambiguous_match", None, ())
                elif snapshot.complete:
                    values[key] = Observation("not_found_in_checked_depth", None, ())
                else:
                    values[key] = Observation("not_observed", None, ())
        return values

    @staticmethod
    def _quality(rows: list[CompetitorSnapshotRow]) -> CoverageQuality:
        if not rows:
            return "insufficient_data"
        if all(row.complete for row in rows):
            return "complete"
        return "partial"

    @staticmethod
    def _site_response(row: SelectedSiteRow) -> CompetitorSelectedSite:
        return CompetitorSelectedSite(
            tracked_site_id=row.site.id,
            name=row.site.name,
            primary_domain=row.primary_domain,
            role=cast(Literal["primary", "competitor"], row.association.role),
        )

    @staticmethod
    def _head_to_head(
        snapshots: list[CompetitorSnapshotRow],
        observations: dict[tuple[UUID, UUID], Observation],
        primary: SelectedSiteRow,
        competitor: SelectedSiteRow,
        top_n: int,
    ) -> HeadToHeadMetric:
        ahead = tied = behind = paired = opportunities = 0
        for snapshot in snapshots:
            mine = observations[(snapshot.check_id, primary.site.id)]
            theirs = observations[(snapshot.check_id, competitor.site.id)]
            if mine.position is not None and theirs.position is not None:
                paired += 1
                if mine.position < theirs.position:
                    ahead += 1
                elif mine.position > theirs.position:
                    behind += 1
                else:
                    tied += 1
            if (
                mine.status == "not_found_in_checked_depth"
                and theirs.position is not None
                and theirs.position <= top_n
            ):
                opportunities += 1
        return HeadToHeadMetric(
            opponent_site_id=competitor.site.id,
            opponent_name=competitor.site.name,
            both_numeric_ranked=paired,
            primary_ahead=ahead,
            tied=tied,
            competitor_ahead=behind,
            excluded_unpaired=len(snapshots) - paired,
            opportunities=opportunities,
        )

    @staticmethod
    def _opponent(
        competitors: list[SelectedSiteRow], opponent_site_id: UUID | None
    ) -> SelectedSiteRow | None:
        if opponent_site_id is None:
            return competitors[0] if competitors else None
        opponent = next(
            (row for row in competitors if row.site.id == opponent_site_id), None
        )
        if opponent is None:
            raise AppError(
                422,
                "INVALID_OPPONENT_SITE",
                "Opponent must be a selected competitor site.",
            )
        return opponent

    def _keyword_row(
        self,
        snapshot: CompetitorSnapshotRow,
        selection: list[SelectedSiteRow],
        observations: dict[tuple[UUID, UUID], Observation],
        primary: SelectedSiteRow,
        opponent: SelectedSiteRow | None,
        top_n: int,
    ) -> CompetitorKeywordRow:
        site_values = [
            self._observation_response(
                snapshot,
                site,
                observations[(snapshot.check_id, site.site.id)],
            )
            for site in selection
        ]
        mine = observations[(snapshot.check_id, primary.site.id)]
        theirs = (
            observations[(snapshot.check_id, opponent.site.id)] if opponent else None
        )
        state: Literal[
            "both_ranked",
            "my_site_ahead",
            "competitor_ahead",
            "tied",
            "not_comparable",
        ] = "not_comparable"
        gap = None
        if mine.position is not None and theirs and theirs.position is not None:
            gap = theirs.position - mine.position
            if gap > 0:
                state = "my_site_ahead"
            elif gap < 0:
                state = "competitor_ahead"
            else:
                state = "tied"
        opportunity = bool(
            theirs
            and mine.status == "not_found_in_checked_depth"
            and theirs.position is not None
            and theirs.position <= top_n
        )
        return CompetitorKeywordRow(
            keyword_id=snapshot.keyword_id,
            keyword=snapshot.keyword,
            checked_at=snapshot.checked_at,
            rank_check_id=snapshot.check_id,
            checked_depth=snapshot.depth,
            snapshot_complete=snapshot.complete,
            sites=site_values,
            opponent_site_id=opponent.site.id if opponent else None,
            position_gap=gap,
            comparison_state=state,
            opportunity=opportunity,
        )

    @staticmethod
    def _observation_response(
        snapshot: CompetitorSnapshotRow,
        site: SelectedSiteRow,
        observation: Observation,
    ) -> CompetitorSiteObservation:
        best = observation.matches[0] if observation.matches else None
        return CompetitorSiteObservation(
            tracked_site_id=site.site.id,
            name=site.site.name,
            status=cast(CompetitorStatus, observation.status),
            position=observation.position,
            checked_depth=snapshot.depth,
            matched_url=best.url
            if best and CompetitorAnalyticsService._safe_url(best.url)
            else None,
            matched_hostname=best.hostname if best else None,
        )

    @staticmethod
    def _safe_url(value: str) -> bool:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return False
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
