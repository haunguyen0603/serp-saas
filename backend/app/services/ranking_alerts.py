"""Durable alert evaluation. Database transactions fence evaluators; no SERP I/O."""

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models.keyword import Keyword
from app.models.project import Project, ProjectStatus
from app.models.rank_check import RankCheck, RankCheckStatus
from app.models.ranking import Ranking
from app.models.ranking_alert import (
    RankingAlert,
    RankingAlertDelivery,
    RankingAlertEvaluation,
)
from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite, TrackedSiteStatus
from app.models.user import User, UserStatus
from app.repositories.ranking_alert import RankingAlertRepository
from app.schemas.ranking_alert import AlertPreferences
from app.services.serp.types import OrganicResult
from app.services.task_queue.base import RankCheckTaskQueue

logger = logging.getLogger(__name__)
TYPE_FLAGS = {
    "entered_top10": "notify_entered_top10",
    "left_top10": "notify_left_top10",
    "rank_improved": "notify_improvement",
    "rank_declined": "notify_decline",
}


def classify(previous: int | None, current: int | None, threshold: int) -> str | None:
    if previous is None and current is not None:
        return "entered_top10"
    if previous is not None and current is None:
        return "left_top10"
    if previous is not None and current is not None:
        if previous - current >= threshold:
            return "rank_improved"
        if current - previous >= threshold:
            return "rank_declined"
    return None


def context_fingerprint(
    project: Project, domains: list[tuple[TrackedDomain, TrackedSite]]
) -> str:
    # Versions prevent comparing A -> B -> A configuration changes.
    context = [
        project.updated_at.isoformat(),
        project.search_engine,
        project.country_code,
        project.language_code,
        project.device,
        project.location,
        sorted(
            (
                str(d.id),
                str(s.id),
                d.domain,
                d.updated_at.isoformat(),
                s.updated_at.isoformat(),
            )
            for d, s in domains
        ),
    ]
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


async def persist_evaluation(
    session: AsyncSession,
    check: RankCheck,
    project: Project,
    domains: list[tuple[TrackedDomain, TrackedSite]],
    results: tuple[OrganicResult, ...],
    rankings: list[Ranking],
) -> None:
    """Part of rank persistence transaction. Partial/legacy observations are unknown."""
    fingerprint = context_fingerprint(project, domains)
    metadata = check.provider_metadata or {}
    if (
        check.status != RankCheckStatus.SUCCEEDED
        or check.result_limit != 10
        or {r.position for r in results} != set(range(1, 11))
        or metadata.get("parsing_warnings", 0) != 0
        or metadata.get("complete", True) is not True
        or check.alert_context != fingerprint
    ):
        return
    positions = {r.tracked_site_id: r.position for r in rankings}
    sites = {
        s.id: {"id": str(s.id), "name": s.name, "position": positions.get(s.id)}
        for _, s in domains
    }
    newer = await session.scalar(
        select(RankingAlertEvaluation.check_id)
        .join(RankCheck, RankCheck.id == RankingAlertEvaluation.check_id)
        .where(
            RankCheck.status == RankCheckStatus.SUCCEEDED,
            RankingAlertEvaluation.keyword_id == check.keyword_id,
            tuple_(RankingAlertEvaluation.observed_at, RankingAlertEvaluation.check_id)
            > tuple_(literal(check.requested_at), literal(check.id)),
        )
        .limit(1)
    )
    await session.execute(
        insert(RankingAlertEvaluation)
        .values(
            check_id=check.id,
            user_id=check.user_id,
            project_id=check.project_id,
            keyword_id=check.keyword_id,
            observed_at=check.requested_at,
            environment=hashlib.sha256(
                (fingerprint + check.query_snapshot).encode()
            ).hexdigest(),
            sites=list(sites.values()),
            suppressed=newer is not None,
        )
        .on_conflict_do_nothing()
    )


class AlertEvaluationService:
    def __init__(
        self, factory: async_sessionmaker[AsyncSession], settings: Settings
    ) -> None:
        self.factory, self.settings = factory, settings

    async def evaluate(self, check_id: UUID) -> bool:
        async with self.factory() as session, session.begin():
            # All work is DB-only and atomic. Crash releases locks and rolls back.
            evaluation = await session.scalar(
                select(RankingAlertEvaluation)
                .where(
                    RankingAlertEvaluation.check_id == check_id,
                    RankingAlertEvaluation.status == "pending",
                    RankingAlertEvaluation.next_attempt_at <= datetime.now(UTC),
                )
                .with_for_update(skip_locked=True)
            )
            if evaluation is None:
                return False
            repo = RankingAlertRepository(session)
            project = await repo.project(
                evaluation.project_id, evaluation.user_id, lock=True
            )
            check = await session.get(RankCheck, check_id)
            keyword = await session.get(Keyword, evaluation.keyword_id)
            user = await session.get(User, evaluation.user_id)
            preferences = await repo.preferences(project.id, evaluation.user_id)
            evaluation.attempts += 1
            history = (
                select(RankingAlertEvaluation)
                .join(RankCheck, RankCheck.id == RankingAlertEvaluation.check_id)
                .where(
                    RankCheck.status == RankCheckStatus.SUCCEEDED,
                    RankingAlertEvaluation.user_id == evaluation.user_id,
                    RankingAlertEvaluation.project_id == evaluation.project_id,
                    RankingAlertEvaluation.keyword_id == evaluation.keyword_id,
                )
            )
            previous = await session.scalar(
                history.where(
                    tuple_(
                        RankingAlertEvaluation.observed_at,
                        RankingAlertEvaluation.check_id,
                    )
                    < tuple_(literal(evaluation.observed_at), literal(check_id))
                )
                .order_by(
                    RankingAlertEvaluation.observed_at.desc(),
                    RankingAlertEvaluation.check_id.desc(),
                )
                .limit(1)
            )
            if (
                self.settings.ranking_alerts_enabled
                and preferences.enabled
                and project.status == ProjectStatus.ACTIVE
                and check
                and check.status == RankCheckStatus.SUCCEEDED
                and keyword
                and keyword.active
                and user
                and user.status == UserStatus.ACTIVE
                and previous
                and previous.environment == evaluation.environment
                and not evaluation.suppressed
            ):
                await self._create(
                    session, evaluation, previous, check, project, preferences, user
                )
            evaluation.status = "completed"
            evaluation.completed_at = datetime.now(UTC)
            evaluation.last_error = None
            logger.info(
                "ranking_alert_evaluation_completed",
                extra={
                    "rank_check_id": str(check_id),
                    "user_id": str(evaluation.user_id),
                    "project_id": str(project.id),
                    "attempts": evaluation.attempts,
                },
            )
        return True

    async def _create(
        self,
        session: AsyncSession,
        current: RankingAlertEvaluation,
        previous: RankingAlertEvaluation,
        check: RankCheck,
        project: Project,
        preferences: AlertPreferences,
        user: User,
    ) -> None:
        old = {str(site["id"]): site for site in previous.sites}
        active_sites = set(
            await session.scalars(
                select(TrackedSite.id).where(
                    TrackedSite.user_id == user.id,
                    TrackedSite.status == TrackedSiteStatus.ACTIVE,
                )
            )
        )
        for site in current.sites:
            identity = str(site["id"])
            if identity not in old or UUID(identity) not in active_sites:
                continue
            before, after = old[identity].get("position"), site.get("position")
            before_rank = int(before) if isinstance(before, int) else None
            after_rank = int(after) if isinstance(after, int) else None
            kind = classify(before_rank, after_rank, preferences.movement_threshold)
            if kind is None or not getattr(preferences, TYPE_FLAGS[kind]):
                continue
            alert_id = await session.scalar(
                insert(RankingAlert)
                .values(
                    user_id=user.id,
                    project_id=project.id,
                    keyword_id=current.keyword_id,
                    tracked_site_id=UUID(identity),
                    site_identity=UUID(identity),
                    alert_type=kind,
                    previous_observation_id=previous.check_id,
                    current_observation_id=current.check_id,
                    previous_rank=before_rank,
                    current_rank=after_rank,
                    rank_delta=before_rank - after_rank
                    if before_rank is not None and after_rank is not None
                    else None,
                    keyword=check.query_snapshot,
                    project_name=project.name,
                    site_name=str(site["name"]),
                    device=check.device_snapshot,
                    observed_at=current.observed_at,
                )
                .on_conflict_do_nothing(constraint="uq_ranking_alert_event")
                .returning(RankingAlert.id)
            )
            if alert_id and preferences.email_enabled and user.email_verified_at:
                session.add(RankingAlertDelivery(alert_id=alert_id))
            logger.info(
                "ranking_alert_created"
                if alert_id
                else "ranking_alert_duplicate_suppressed",
                extra={
                    "rank_check_id": str(current.check_id),
                    "alert_type": kind,
                    "user_id": str(user.id),
                },
            )

    async def drain(self, limit: int = 100) -> int:
        async with self.factory() as session:
            ids = list(
                await session.scalars(
                    select(RankingAlertEvaluation.check_id)
                    .where(
                        RankingAlertEvaluation.status == "pending",
                        RankingAlertEvaluation.next_attempt_at <= datetime.now(UTC),
                    )
                    .order_by(
                        RankingAlertEvaluation.observed_at,
                        RankingAlertEvaluation.check_id,
                    )
                    .limit(limit)
                )
            )
        count = 0
        for check_id in ids:
            try:
                count += await self.evaluate(check_id)
            except Exception:
                # Never log exception text: DB parameters can contain PII.
                logger.warning(
                    "ranking_alert_evaluation_failed",
                    extra={"rank_check_id": str(check_id)},
                )
                async with self.factory() as session, session.begin():
                    row = await session.get(
                        RankingAlertEvaluation, check_id, with_for_update=True
                    )
                    if row and row.status == "pending":
                        row.attempts += 1
                        row.last_error = "ALERT_EVALUATION_FAILED"
                        row.status = "failed" if row.attempts >= 5 else "pending"
                        row.next_attempt_at = datetime.now(UTC) + timedelta(
                            seconds=30 * 2**row.attempts
                        )
        return count


async def enqueue_alerts(queue: RankCheckTaskQueue) -> None:
    """Coalesce keyword events into one sweep per minute; scheduler repairs misses."""
    try:
        await queue.enqueue_ranking_alerts(
            attempt=int(datetime.now(UTC).timestamp()) // 60
        )
    except Exception:
        logger.warning("ranking_alert_enqueue_failed")


async def alert_backlog(factory: async_sessionmaker[AsyncSession]) -> dict[str, object]:
    """Aggregate operator metrics only; never exposes keyword or recipient text."""
    async with factory() as session:
        evaluations = (
            await session.execute(
                select(
                    RankingAlertEvaluation.status,
                    func.count(),
                    func.min(RankingAlertEvaluation.created_at),
                ).group_by(RankingAlertEvaluation.status)
            )
        ).all()
        deliveries = (
            await session.execute(
                select(
                    RankingAlertDelivery.status,
                    func.count(),
                    func.min(RankingAlertDelivery.next_attempt_at),
                ).group_by(RankingAlertDelivery.status)
            )
        ).all()
        unread = await session.scalar(
            select(func.count())
            .select_from(RankingAlert)
            .where(RankingAlert.read_at.is_(None))
        )
        types = (
            await session.execute(
                select(RankingAlert.alert_type, func.count()).group_by(
                    RankingAlert.alert_type
                )
            )
        ).all()
    return {
        "evaluations": [
            {
                "status": status,
                "count": count,
                "oldest_created_at": oldest.isoformat() if oldest else None,
            }
            for status, count, oldest in evaluations
        ],
        "deliveries": [
            {
                "status": status,
                "count": count,
                "oldest_due_at": oldest.isoformat() if oldest else None,
            }
            for status, count, oldest in deliveries
        ],
        "unread_count": unread or 0,
        "alerts_by_type": {kind: count for kind, count in types},
    }
