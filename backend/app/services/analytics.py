from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from app.core.errors import AppError
from app.models.project import Project
from app.repositories.analytics import AnalyticsRepository, KeywordObservationPair
from app.repositories.keyword import KeywordRepository
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.schemas.analytics import (
    AnalyticsRange,
    HistoryTrackedSite,
    KeywordRankingHistoryResponse,
    MovementBasis,
    ProjectAnalyticsSummaryResponse,
    RankingDistributionResponse,
    RankingHistoryPoint,
    RankingMover,
    RankingMoversResponse,
)

_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}


class ProjectAnalyticsService:
    def __init__(
        self,
        analytics: AnalyticsRepository,
        projects: ProjectRepository,
        keywords: KeywordRepository,
        tracked_sites: TrackedSiteRepository,
        organizations: KeywordOrganizationRepository | None = None,
    ) -> None:
        self.analytics = analytics
        self.projects = projects
        self.keywords = keywords
        self.tracked_sites = tracked_sites
        self.organizations = organizations

    @staticmethod
    def _range(value: str) -> AnalyticsRange:
        if value not in _RANGE_DAYS:
            raise AppError(
                422,
                "INVALID_ANALYTICS_RANGE",
                "Analytics range must be 7d, 30d, or 90d.",
            )
        return cast(AnalyticsRange, value)

    async def _scope(
        self, project_id: UUID, user_id: UUID, device: str | None
    ) -> tuple[Project, str]:
        project = await self.projects.get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        selected = device or project.device
        if selected not in {"desktop", "mobile"} or selected != project.device:
            raise AppError(
                422,
                "INVALID_DEVICE_SCOPE",
                "Analytics device must match the Project environment.",
            )
        return project, selected

    @staticmethod
    def _buckets(
        observations: list[KeywordObservationPair], effective_depth: int
    ) -> dict[str, int]:
        buckets = {"top_3": 0}
        if effective_depth >= 4:
            buckets["positions_4_10"] = 0
        if effective_depth >= 11:
            buckets["positions_11_20"] = 0
        if effective_depth >= 21:
            buckets["positions_21_50"] = 0
        if effective_depth >= 51:
            buckets["positions_51_100"] = 0
        buckets["not_found_in_depth"] = 0
        for item in observations:
            position = item.current_position
            if position is None or position > effective_depth:
                buckets["not_found_in_depth"] += 1
            elif position <= 3:
                buckets["top_3"] += 1
            elif position <= 10:
                buckets["positions_4_10"] += 1
            elif position <= 20:
                buckets["positions_11_20"] += 1
            elif position <= 50:
                buckets["positions_21_50"] += 1
            else:
                buckets["positions_51_100"] += 1
        return buckets

    async def get_summary(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        device: str | None,
        range_value: str,
        group_filter: UUID | None = None,
        tag_ids: frozenset[UUID] = frozenset(),
    ) -> ProjectAnalyticsSummaryResponse:
        selected_range = self._range(range_value)
        _, selected_device = await self._scope(project_id, user_id, device)
        as_of = datetime.now(UTC)
        boundary = as_of - timedelta(days=_RANGE_DAYS[selected_range])
        observations = await self.analytics.keyword_observations(
            project_id,
            user_id,
            selected_device,
            boundary,
            group_filter=group_filter,
            tag_ids=tag_ids,
        )
        total_keywords = await self.analytics.active_keyword_count(
            project_id, group_filter=group_filter, tag_ids=tag_ids
        )
        effective_depth = min((item.current_depth for item in observations), default=10)
        buckets = self._buckets(observations, effective_depth)
        movement = {
            "improved": 0,
            "declined": 0,
            "unchanged": 0,
            "newly_ranked": 0,
            "lost_ranking": 0,
            "no_previous_data": total_keywords - len(observations),
        }
        bases: set[str] = set()
        for item in observations:
            if not item.has_previous:
                movement["no_previous_data"] += 1
                continue
            bases.add(
                "range_boundary"
                if item.previous_before_boundary
                else "earliest_in_range"
            )
            if item.previous_position is None and item.current_position is not None:
                movement["newly_ranked"] += 1
            elif item.previous_position is not None and item.current_position is None:
                movement["lost_ranking"] += 1
            elif item.previous_position is None:
                movement["unchanged"] += 1
            else:
                assert item.current_position is not None
                assert item.previous_position is not None
                if item.current_position < item.previous_position:
                    movement["improved"] += 1
                elif item.current_position > item.previous_position:
                    movement["declined"] += 1
                else:
                    movement["unchanged"] += 1
        # Reconciliation invariant: each active Keyword has exactly one movement
        # state, including never-checked Keywords as no_previous_data.
        assert sum(movement.values()) == total_keywords
        basis = (
            "none"
            if not bases
            else "earliest_in_range"
            if "earliest_in_range" in bases
            else "range_boundary"
        )
        top_3 = buckets["top_3"]
        top_10 = top_3 + buckets.get("positions_4_10", 0)
        ranked_keywords = sum(
            item.current_position is not None
            and item.current_position <= effective_depth
            for item in observations
        )
        return ProjectAnalyticsSummaryResponse(
            project_id=project_id,
            device=selected_device,
            range=selected_range,
            as_of=as_of,
            comparison_basis=cast(MovementBasis, basis),
            total_keywords=total_keywords,
            observed_keywords=len(observations),
            never_checked=total_keywords - len(observations),
            ranked_keywords=ranked_keywords,
            not_found_in_depth=buckets["not_found_in_depth"],
            top_3=top_3,
            top_10=top_10,
            improved=movement["improved"],
            declined=movement["declined"],
            unchanged=movement["unchanged"],
            newly_ranked=movement["newly_ranked"],
            lost_ranking=movement["lost_ranking"],
            entered_checked_depth=movement["newly_ranked"],
            left_checked_depth=movement["lost_ranking"],
            no_previous_data=movement["no_previous_data"],
            distribution=RankingDistributionResponse(
                effective_depth=effective_depth, buckets=buckets
            ),
        )

    async def get_organization_summary(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        device: str | None,
        range_value: str,
        group_id: UUID | None,
        tag_id: UUID | None,
    ) -> ProjectAnalyticsSummaryResponse:
        if (group_id is None) == (tag_id is None):
            raise AppError(
                422,
                "INVALID_ORGANIZATION_SCOPE",
                "Select exactly one Group or Tag.",
            )
        await self._scope(project_id, user_id, device)
        if self.organizations is None:
            raise AppError(
                503, "ORGANIZATION_UNAVAILABLE", "Organization is unavailable."
            )
        if (
            group_id is not None
            and len(await self.organizations.groups_for_project(project_id, {group_id}))
            != 1
        ):
            raise AppError(422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid.")
        selected_tags = frozenset({tag_id}) if tag_id is not None else frozenset()
        if (
            tag_id is not None
            and len(await self.organizations.tags_for_project(project_id, {tag_id}))
            != 1
        ):
            raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
        return await self.get_summary(
            project_id,
            user_id,
            device=device,
            range_value=range_value,
            group_filter=group_id,
            tag_ids=selected_tags,
        )

    async def get_distribution(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        device: str | None,
        range_value: str,
    ) -> RankingDistributionResponse:
        return (
            await self.get_summary(
                project_id,
                user_id,
                device=device,
                range_value=range_value,
            )
        ).distribution

    async def get_movers(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        device: str | None,
        range_value: str,
        limit: int,
    ) -> RankingMoversResponse:
        selected_range = self._range(range_value)
        _, selected_device = await self._scope(project_id, user_id, device)
        if not 1 <= limit <= 50:
            raise AppError(422, "VALIDATION_ERROR", "Limit must be from 1 to 50.")
        boundary = datetime.now(UTC) - timedelta(days=_RANGE_DAYS[selected_range])
        winners = await self.analytics.movers(
            project_id,
            user_id,
            selected_device,
            boundary,
            winner=True,
            limit=limit,
        )
        losers = await self.analytics.movers(
            project_id,
            user_id,
            selected_device,
            boundary,
            winner=False,
            limit=limit,
        )
        return RankingMoversResponse(
            winners=[RankingMover(**row.__dict__) for row in winners],
            losers=[RankingMover(**row.__dict__) for row in losers],
        )

    async def get_keyword_history(
        self,
        project_id: UUID,
        keyword_id: UUID,
        user_id: UUID,
        *,
        tracked_site_id: UUID,
        device: str | None,
        range_value: str,
    ) -> KeywordRankingHistoryResponse:
        selected_range = self._range(range_value)
        _, selected_device = await self._scope(project_id, user_id, device)
        keyword = await self.keywords.get_for_user_project(
            keyword_id, project_id, user_id
        )
        if keyword is None:
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
        tracked_site = await self.tracked_sites.get_for_user(tracked_site_id, user_id)
        if tracked_site is None:
            raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
        start = max(
            datetime.now(UTC) - timedelta(days=_RANGE_DAYS[selected_range]),
            tracked_site.created_at,
        )
        rows = await self.analytics.keyword_history(
            project_id,
            keyword_id,
            user_id,
            tracked_site_id,
            selected_device,
            start,
        )
        return KeywordRankingHistoryResponse(
            keyword_id=keyword.id,
            keyword=keyword.keyword,
            tracked_site=HistoryTrackedSite(id=tracked_site.id, name=tracked_site.name),
            device=selected_device,
            range=selected_range,
            points=[
                RankingHistoryPoint(
                    checked_at=row.checked_at,
                    position=row.position,
                    status=(
                        "ranked" if row.position is not None else "not_found_in_depth"
                    ),
                    checked_depth=row.checked_depth,
                    rank_check_id=row.rank_check_id,
                )
                for row in rows
            ],
        )
