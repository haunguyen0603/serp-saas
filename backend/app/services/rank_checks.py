import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.models.keyword import Keyword
from app.models.project import Project, ProjectStatus
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.rank_check_provider_attempt import RankCheckProviderAttempt
from app.models.rank_check_result import RankCheckResult
from app.models.ranking import Ranking
from app.repositories.keyword import KeywordRepository
from app.repositories.project import ProjectRepository
from app.repositories.rank_check import RankCheckRepository
from app.repositories.rank_check_provider_attempt import (
    RankCheckProviderAttemptRepository,
)
from app.repositories.rank_check_result import RankCheckResultRepository
from app.repositories.ranking import RankingRepository
from app.repositories.tracked_domain import TrackedDomainRepository
from app.schemas.rank_check import (
    LatestKeywordRanking,
    LatestRankingResponse,
    ProjectRankCheckOutcome,
    ProjectRankCheckRequest,
    ProjectRankCheckResponse,
    RankCheckDetailResponse,
    RankCheckListResponse,
    RankCheckResponse,
    RankCheckStatusFilter,
)
from app.services.domain_matching import DomainMatcher, MatchableDomain
from app.services.job_execution import JobExecution
from app.services.normalization import decode_cursor, encode_cursor
from app.services.ranking_alerts import (
    context_fingerprint,
    enqueue_alerts,
    persist_evaluation,
)
from app.services.serp import OrganicResult, SerpProviderError, SerpSearchRequest
from app.services.serp.router import ProviderRouter
from app.services.task_queue import create_task_queue

logger = logging.getLogger(__name__)

_PROVIDER_HTTP_STATUS = {
    "SERP_PROVIDER_NOT_CONFIGURED": 503,
    "SERP_PROVIDER_TIMEOUT": 503,
    "SERP_PROVIDER_UNAVAILABLE": 503,
    "SERP_PROVIDER_RATE_LIMITED": 503,
    "SERP_PROVIDER_QUOTA_EXHAUSTED": 503,
    "SERP_PROVIDER_BUDGET_EXHAUSTED": 503,
    "SERP_NO_PROVIDER_AVAILABLE": 503,
    "SERP_PROVIDER_UNSUPPORTED_CONFIGURATION": 503,
    "SERP_PROVIDER_AUTH_ERROR": 502,
    "SERP_PROVIDER_INVALID_REQUEST": 502,
    "SERP_PROVIDER_INVALID_RESPONSE": 502,
    "SERP_PROVIDER_ERROR": 502,
}


class RankCheckExecutionService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: ProviderRouter,
        settings: Settings,
        matcher: DomainMatcher | None = None,
        job_execution: JobExecution | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.provider = provider
        self.settings = settings
        self.matcher = matcher or DomainMatcher()
        self.job_execution = job_execution

    async def run_keyword(
        self, project_id: UUID, keyword_id: UUID, user_id: UUID
    ) -> RankCheckDetailResponse:
        response = await self._execute(project_id, keyword_id, user_id)
        if response.status is RankCheckStatus.FAILED:
            code = response.error_code or "SERP_PROVIDER_ERROR"
            raise AppError(
                _PROVIDER_HTTP_STATUS.get(code, 500),
                code,
                response.error_message or "The rank check failed.",
            )
        return response

    async def run_project(
        self,
        project_id: UUID,
        user_id: UUID,
        request: ProjectRankCheckRequest,
    ) -> ProjectRankCheckResponse:
        keywords = await self._project_keywords(
            project_id, user_id, request.keyword_ids
        )
        if len(keywords) > self.settings.serp_manual_project_keyword_limit:
            raise AppError(
                400,
                "RANK_CHECK_LIMIT_EXCEEDED",
                "A manual Project check is limited to "
                f"{self.settings.serp_manual_project_keyword_limit} keywords.",
            )
        semaphore = asyncio.Semaphore(self.settings.serp_max_concurrent_requests)

        async def execute(keyword: Keyword) -> ProjectRankCheckOutcome:
            async with semaphore:
                try:
                    check = await self._execute(project_id, keyword.id, user_id)
                    return ProjectRankCheckOutcome(
                        keyword_id=keyword.id,
                        check=check,
                        error_code=check.error_code,
                    )
                except AppError as error:
                    return ProjectRankCheckOutcome(
                        keyword_id=keyword.id, check=None, error_code=error.code
                    )

        outcomes = await asyncio.gather(*(execute(keyword) for keyword in keywords))
        succeeded = sum(
            outcome.check is not None
            and outcome.check.status is RankCheckStatus.SUCCEEDED
            for outcome in outcomes
        )
        return ProjectRankCheckResponse(
            project_id=project_id,
            submitted_keywords=len(keywords),
            succeeded=succeeded,
            failed=len(keywords) - succeeded,
            checks=outcomes,
        )

    async def _project_keywords(
        self, project_id: UUID, user_id: UUID, requested: list[UUID] | None
    ) -> list[Keyword]:
        async with self.session_factory() as session:
            project = await ProjectRepository(session).get_for_user(project_id, user_id)
            if project is None:
                raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
            if project.status is not ProjectStatus.ACTIVE:
                raise AppError(400, "PROJECT_NOT_ACTIVE", "The Project is archived.")
            repository = KeywordRepository(session)
            if requested is None:
                return await repository.list_active_for_user_project(
                    project_id, user_id
                )
            unique_ids = list(dict.fromkeys(requested))
            keywords: list[Keyword] = []
            for keyword_id in unique_ids:
                keyword = await repository.get_for_user_project(
                    keyword_id, project_id, user_id
                )
                if keyword is None:
                    raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
                if not keyword.active:
                    raise AppError(400, "KEYWORD_NOT_ACTIVE", "The Keyword is paused.")
                keywords.append(keyword)
            return keywords

    async def execute_rank_check(
        self, project_id: UUID, keyword_id: UUID, user_id: UUID
    ) -> RankCheckDetailResponse:
        return await self._execute(project_id, keyword_id, user_id)

    async def _execute(
        self, project_id: UUID, keyword_id: UUID, user_id: UUID
    ) -> RankCheckDetailResponse:
        check, search_request = await self._start(project_id, keyword_id, user_id)
        logger.info(
            "rank_check_started",
            extra={
                "user_id": str(user_id),
                "project_id": str(project_id),
                "keyword_id": str(keyword_id),
                "rank_check_id": str(check.id),
                "provider": self.provider.name,
            },
        )
        try:
            provider_result = await self.provider.search(search_request, check.id)
        except SerpProviderError as error:
            logger.warning(
                "serp_provider_error",
                extra={
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "keyword_id": str(keyword_id),
                    "rank_check_id": str(check.id),
                    "provider": error.provider or self.provider.name,
                    "error_code": error.code,
                },
            )
            return await self._fail(
                check.id,
                project_id,
                user_id,
                error.code,
                error.safe_message,
                error.request_count,
                error.provider,
            )
        except Exception:
            logger.warning(
                "serp_provider_error",
                extra={
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "keyword_id": str(keyword_id),
                    "rank_check_id": str(check.id),
                    "provider": self.provider.name,
                    "error_code": "SERP_PROVIDER_ERROR",
                },
            )
            return await self._fail(
                check.id,
                project_id,
                user_id,
                "SERP_PROVIDER_ERROR",
                "The SERP provider could not complete the search.",
                0,
                None,
            )

        bounded = self._bounded_results(
            provider_result.organic_results, search_request.result_limit
        )
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    if self.job_execution:
                        await self.job_execution.lock(session)
                    checks = RankCheckRepository(session)
                    stored = await checks.get_owned(
                        check.id, project_id, user_id, for_update=True
                    )
                    if stored is None:
                        raise RuntimeError("Rank check disappeared before persistence")
                    project = await session.get(
                        Project, project_id, with_for_update=True
                    )
                    if project is None:
                        raise RuntimeError("Project disappeared before persistence")
                    domain_rows = await TrackedDomainRepository(
                        session
                    ).list_active_for_matching(user_id)
                    matchable = [
                        MatchableDomain(
                            tracked_site_id=site.id,
                            tracked_domain_id=domain.id,
                            tracked_site_name=site.name,
                            domain=domain.domain,
                        )
                        for domain, site in domain_rows
                    ]
                    matches = self.matcher.match(bounded, matchable)
                    logger.info(
                        "domain_matches_found",
                        extra={
                            "user_id": str(user_id),
                            "project_id": str(project_id),
                            "keyword_id": str(keyword_id),
                            "rank_check_id": str(check.id),
                            "provider": provider_result.provider,
                            "result_count": len(bounded),
                            "match_count": len(matches),
                        },
                    )
                    results = await RankCheckResultRepository(session).create_many(
                        stored.id, bounded
                    )
                    rankings = await RankingRepository(session).create_many(
                        stored.id, matches
                    )
                    request_count = provider_result.provider_request_count
                    if self.job_execution:
                        request_count = int(
                            await session.scalar(
                                select(
                                    func.coalesce(
                                        func.sum(
                                            RankCheckProviderAttempt.provider_request_count
                                        ),
                                        0,
                                    )
                                ).where(
                                    RankCheckProviderAttempt.rank_check_id == stored.id
                                )
                            )
                            or 0
                        )
                    await checks.mark_succeeded(
                        stored,
                        provider=provider_result.provider,
                        provider_request_id=provider_result.provider_request_id,
                        provider_metadata=provider_result.raw_metadata,
                        provider_request_count=request_count,
                        completed_at=provider_result.completed_at,
                    )
                    await persist_evaluation(
                        session, stored, project, domain_rows, bounded, rankings
                    )
            logger.info(
                "rank_check_succeeded",
                extra={
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "keyword_id": str(keyword_id),
                    "rank_check_id": str(check.id),
                    "provider": provider_result.provider,
                    "result_count": len(results),
                    "match_count": len(rankings),
                },
            )
            try:
                await enqueue_alerts(create_task_queue(self.settings))
            except Exception:
                logger.warning("ranking_alert_enqueue_failed")
            attempts = await self._attempts(check.id)
            return RankCheckDetailResponse.from_check_detail(
                stored, results, rankings, attempts
            )
        except Exception:
            await self._fail(
                check.id,
                project_id,
                user_id,
                "RANK_CHECK_PERSISTENCE_ERROR",
                "The rank check results could not be saved.",
                provider_result.provider_request_count,
                provider_result.provider,
            )
            raise AppError(
                500,
                "RANK_CHECK_PERSISTENCE_ERROR",
                "The rank check results could not be saved.",
            ) from None

    async def _start(
        self, project_id: UUID, keyword_id: UUID, user_id: UUID
    ) -> tuple[RankCheck, SerpSearchRequest]:
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    job = (
                        await self.job_execution.lock(session)
                        if self.job_execution
                        else None
                    )
                    project = await ProjectRepository(session).get_for_user(
                        project_id, user_id
                    )
                    if project is None:
                        raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
                    if project.status is not ProjectStatus.ACTIVE:
                        raise AppError(
                            400, "PROJECT_NOT_ACTIVE", "The Project is archived."
                        )
                    keyword = await KeywordRepository(session).get_for_user_project(
                        keyword_id, project_id, user_id
                    )
                    if keyword is None:
                        raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
                    if not keyword.active:
                        raise AppError(
                            400, "KEYWORD_NOT_ACTIVE", "The Keyword is paused."
                        )
                    if job is not None:
                        from app.services.billing.usage import UsageService

                        if not await UsageService(session).settle(job.id, True):
                            raise AppError(
                                409,
                                "USAGE_LIMIT_EXCEEDED",
                                "No valid usage reservation exists for this Job.",
                            )
                    requested_at = datetime.now(UTC)
                    previous = (
                        await session.get(RankCheck, job.rank_check_id)
                        if job and job.rank_check_id
                        else None
                    )
                    if previous is not None:
                        previous.status = RankCheckStatus.RUNNING
                        previous.completed_at = None
                        previous.error_code = None
                        previous.error_message = None
                        return previous, SerpSearchRequest(
                            query=previous.query_snapshot,
                            search_engine=previous.search_engine_snapshot,
                            country_code=previous.country_code_snapshot,
                            language_code=previous.language_code_snapshot,
                            device=previous.device_snapshot,
                            location=previous.location_snapshot,
                            result_limit=previous.result_limit,
                        )
                    check = await RankCheckRepository(session).create_running(
                        user_id=user_id,
                        project_id=project.id,
                        keyword_id=keyword.id,
                        provider=self.provider.name,
                        query=keyword.keyword,
                        search_engine=project.search_engine,
                        country_code=project.country_code,
                        language_code=project.language_code,
                        device=project.device,
                        location=project.location,
                        result_limit=self.settings.serp_default_result_limit,
                        requested_at=requested_at,
                    )
                    domains = await TrackedDomainRepository(
                        session
                    ).list_active_for_matching(user_id)
                    check.alert_context = context_fingerprint(project, domains)
                    if job is not None:
                        job.rank_check_id = check.id
                    request = SerpSearchRequest(
                        query=keyword.keyword,
                        search_engine=project.search_engine,
                        country_code=project.country_code,
                        language_code=project.language_code,
                        device=project.device,
                        location=project.location,
                        result_limit=self.settings.serp_default_result_limit,
                    )
            return check, request
        except IntegrityError:
            raise AppError(
                409,
                "RANK_CHECK_ALREADY_RUNNING",
                "A rank check is already running for this Keyword.",
            ) from None

    async def _fail(
        self,
        check_id: UUID,
        project_id: UUID,
        user_id: UUID,
        code: str,
        message: str,
        request_count: int,
        provider: str | None,
    ) -> RankCheckDetailResponse:
        async with self.session_factory() as session:
            async with session.begin():
                if self.job_execution:
                    await self.job_execution.lock(session)
                repository = RankCheckRepository(session)
                check = await repository.get_owned(
                    check_id, project_id, user_id, for_update=True
                )
                if check is None:
                    raise RuntimeError("Rank check disappeared before failure update")
                if self.job_execution:
                    request_count = int(
                        await session.scalar(
                            select(
                                func.coalesce(
                                    func.sum(
                                        RankCheckProviderAttempt.provider_request_count
                                    ),
                                    0,
                                )
                            ).where(RankCheckProviderAttempt.rank_check_id == check.id)
                        )
                        or 0
                    )
                await repository.mark_failed(
                    check,
                    provider=provider,
                    code=code,
                    message=message,
                    provider_request_count=request_count,
                    completed_at=datetime.now(UTC),
                )
        logger.warning(
            "rank_check_failed",
            extra={
                "user_id": str(user_id),
                "project_id": str(project_id),
                "keyword_id": str(check.keyword_id),
                "rank_check_id": str(check.id),
                "provider": check.provider,
            },
        )
        attempts = await self._attempts(check.id)
        return RankCheckDetailResponse.from_check_detail(check, [], [], attempts)

    async def _attempts(self, check_id: UUID) -> list[RankCheckProviderAttempt]:
        async with self.session_factory() as session:
            return await RankCheckProviderAttemptRepository(session).list_for_checks(
                [check_id]
            )

    @staticmethod
    def _bounded_results(
        results: tuple[OrganicResult, ...], result_limit: int
    ) -> tuple[OrganicResult, ...]:
        unique: dict[int, OrganicResult] = {}
        for result in results:
            if 1 <= result.position <= result_limit:
                unique.setdefault(result.position, result)
        return tuple(unique[position] for position in sorted(unique)[:result_limit])


class RankCheckQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def history(
        self,
        project_id: UUID,
        keyword_id: UUID,
        user_id: UUID,
        *,
        status: RankCheckStatusFilter,
        limit: int,
        cursor: str | None,
    ) -> RankCheckListResponse:
        await self._require_keyword(project_id, keyword_id, user_id)
        selected = None if status == "all" else RankCheckStatus(status)
        checks, has_more = await RankCheckRepository(self.session).list_history(
            project_id,
            keyword_id,
            user_id,
            status=selected,
            limit=limit,
            cursor=decode_cursor(cursor),
        )
        results, rankings, attempts = await self._children(checks)
        next_cursor = (
            encode_cursor(checks[-1].created_at, checks[-1].id)
            if has_more and checks
            else None
        )
        return RankCheckListResponse(
            items=[
                RankCheckResponse.from_check(
                    check, results[check.id], rankings[check.id], attempts[check.id]
                )
                for check in checks
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def detail(
        self, project_id: UUID, keyword_id: UUID, check_id: UUID, user_id: UUID
    ) -> RankCheckDetailResponse:
        await self._require_keyword(project_id, keyword_id, user_id)
        check = await RankCheckRepository(self.session).get_owned(
            check_id, project_id, user_id, keyword_id=keyword_id
        )
        if check is None:
            raise AppError(404, "RANK_CHECK_NOT_FOUND", "Rank Check not found.")
        results, rankings, attempts = await self._children([check])
        return RankCheckDetailResponse.from_check_detail(
            check, results[check.id], rankings[check.id], attempts[check.id]
        )

    async def latest(self, project_id: UUID, user_id: UUID) -> LatestRankingResponse:
        project = await ProjectRepository(self.session).get_for_user(
            project_id, user_id
        )
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        keywords = await KeywordRepository(self.session).list_active_for_user_project(
            project_id, user_id
        )
        checks = await RankCheckRepository(self.session).latest_for_project(
            project_id, user_id
        )
        check_by_keyword = {check.keyword_id: check for check in checks}
        results, rankings, attempts = await self._children(checks)
        return LatestRankingResponse(
            items=[
                LatestKeywordRanking(
                    keyword_id=keyword.id,
                    keyword=keyword.keyword,
                    latest_check=(
                        RankCheckResponse.from_check(
                            check_by_keyword[keyword.id],
                            results[check_by_keyword[keyword.id].id],
                            rankings[check_by_keyword[keyword.id].id],
                            attempts[check_by_keyword[keyword.id].id],
                        )
                        if keyword.id in check_by_keyword
                        else None
                    ),
                )
                for keyword in keywords
            ]
        )

    async def _require_keyword(
        self, project_id: UUID, keyword_id: UUID, user_id: UUID
    ) -> None:
        if (
            await KeywordRepository(self.session).get_for_user_project(
                keyword_id, project_id, user_id
            )
            is None
        ):
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")

    async def _children(
        self, checks: list[RankCheck]
    ) -> tuple[
        dict[UUID, list[RankCheckResult]],
        dict[UUID, list[Ranking]],
        dict[UUID, list[RankCheckProviderAttempt]],
    ]:
        ids = [check.id for check in checks]
        result_rows = await RankCheckResultRepository(self.session).list_for_checks(ids)
        ranking_rows = await RankingRepository(self.session).list_for_checks(ids)
        attempt_rows = await RankCheckProviderAttemptRepository(
            self.session
        ).list_for_checks(ids)
        results: dict[UUID, list[RankCheckResult]] = defaultdict(list)
        rankings: dict[UUID, list[Ranking]] = defaultdict(list)
        attempts: dict[UUID, list[RankCheckProviderAttempt]] = defaultdict(list)
        for result in result_rows:
            results[result.rank_check_id].append(result)
        for ranking in ranking_rows:
            rankings[ranking.rank_check_id].append(ranking)
        for attempt in attempt_rows:
            attempts[attempt.rank_check_id].append(attempt)
        return results, rankings, attempts
