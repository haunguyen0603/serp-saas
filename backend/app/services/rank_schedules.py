import logging
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.errors import AppError
from app.models.project import ProjectStatus
from app.models.rank_job import ProjectRankSchedule, RankCheckBatch
from app.repositories.billing import BillingRepository
from app.repositories.project import ProjectRepository
from app.repositories.rank_job import TERMINAL_BATCHES, RankJobRepository
from app.schemas.rank_job import ScheduleRequest, ScheduleResponse
from app.services.billing.entitlements import EntitlementService
from app.services.billing.reconciliation import reconcile_subscriptions
from app.services.rank_batches import RankBatchService

logger = logging.getLogger(__name__)


def next_run(
    now: datetime, frequency: str, local_time: str, timezone: str, weekday: int = 0
) -> datetime:
    """One run per local day; DST gaps shift forward, folds use first occurrence."""
    zone = ZoneInfo(timezone)
    day = now.astimezone(zone).date()
    clock = time.fromisoformat(local_time)
    for offset in range(15):
        candidate_day = day + timedelta(days=offset)
        if frequency == "weekly" and candidate_day.weekday() != weekday:
            continue
        candidate = datetime.combine(candidate_day, clock, zone).astimezone(UTC)
        if candidate > now:
            return candidate
    raise ValueError("Unable to compute next schedule")


class RankScheduleService:
    def __init__(self, batches: RankBatchService) -> None:
        self.batches = batches

    async def get(self, project_id: UUID, user_id: UUID) -> ScheduleResponse | None:
        async with self.batches.factory() as session:
            await RankJobRepository(session).require_project(project_id, user_id)
            schedule = await session.scalar(
                select(ProjectRankSchedule).where(
                    ProjectRankSchedule.project_id == project_id,
                    ProjectRankSchedule.user_id == user_id,
                )
            )
            return ScheduleResponse.model_validate(schedule) if schedule else None

    async def put(
        self, project_id: UUID, user_id: UUID, request: ScheduleRequest
    ) -> ScheduleResponse:
        async with self.batches.factory() as session, session.begin():
            await BillingRepository(session).lock(user_id)
            project = await ProjectRepository(session).get_for_user(project_id, user_id)
            if project is None:
                raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
            if request.enabled:
                await EntitlementService(session).schedule(
                    user_id, project.device, request.frequency
                )
            # Serialize first-time schedule creation by locking the parent.
            await session.refresh(project, with_for_update={"key_share": True})
            if project.status != ProjectStatus.ACTIVE:
                raise AppError(400, "PROJECT_NOT_ACTIVE", "The Project is archived.")
            schedule = await session.scalar(
                select(ProjectRankSchedule)
                .where(
                    ProjectRankSchedule.project_id == project_id,
                    ProjectRankSchedule.user_id == user_id,
                )
                .with_for_update()
            )
            if schedule is None:
                schedule = ProjectRankSchedule(project_id=project_id, user_id=user_id)
                session.add(schedule)
            for key, value in request.model_dump().items():
                setattr(schedule, key, value)
            schedule.next_run_at = next_run(
                datetime.now(UTC),
                request.frequency,
                request.local_time,
                request.timezone,
                request.weekday,
            )
            await session.flush()
            return ScheduleResponse.model_validate(schedule)

    async def delete(self, project_id: UUID, user_id: UUID) -> None:
        async with self.batches.factory() as session, session.begin():
            await RankJobRepository(session).require_project(project_id, user_id)
            schedule = await session.scalar(
                select(ProjectRankSchedule)
                .where(
                    ProjectRankSchedule.project_id == project_id,
                    ProjectRankSchedule.user_id == user_id,
                )
                .with_for_update()
            )
            if schedule:
                await session.delete(schedule)

    async def dispatch(self, now: datetime | None = None, limit: int = 100) -> int:
        now = now or datetime.now(UTC)
        count = 0
        async with self.batches.factory() as session, session.begin():
            await reconcile_subscriptions(session, now)
        # Each transaction contains only DB operations; queue I/O is recovery's job.
        for _ in range(limit):
            async with self.batches.factory() as session, session.begin():
                schedule = await session.scalar(
                    select(ProjectRankSchedule)
                    .where(
                        ProjectRankSchedule.enabled.is_(True),
                        ProjectRankSchedule.next_run_at <= now,
                    )
                    .order_by(ProjectRankSchedule.next_run_at)
                    .limit(1)
                )
                if schedule is None:
                    break
                await BillingRepository(session).lock(schedule.user_id)
                await session.refresh(schedule, with_for_update=True)
                if not schedule.enabled or schedule.next_run_at > now:
                    continue
                occurrence = schedule.next_run_at
                schedule.next_run_at = next_run(
                    now,
                    schedule.frequency,
                    schedule.local_time,
                    schedule.timezone,
                    schedule.weekday,
                )
                logger.info(
                    "rank_schedule_due", extra={"project_id": str(schedule.project_id)}
                )
                overlap = await session.scalar(
                    select(RankCheckBatch.id)
                    .where(
                        RankCheckBatch.project_id == schedule.project_id,
                        RankCheckBatch.trigger_type == "scheduled",
                        RankCheckBatch.status.not_in(TERMINAL_BATCHES),
                    )
                    .limit(1)
                )
                if overlap:
                    continue
                try:
                    await self.batches.create_rows(
                        session,
                        schedule.project_id,
                        schedule.user_id,
                        None,
                        "scheduled",
                        schedule_id=schedule.id,
                        scheduled_for=occurrence,
                    )
                except AppError as error:
                    if error.code == "PROJECT_NOT_ACTIVE":
                        schedule.enabled = False
                    logger.info(
                        "rank_schedule_skipped",
                        extra={
                            "project_id": str(schedule.project_id),
                            "safe_error_code": error.code,
                        },
                    )
                    continue
                schedule.last_enqueued_at = now
                count += 1
                logger.info(
                    "rank_schedule_dispatched",
                    extra={"project_id": str(schedule.project_id)},
                )
        return count
