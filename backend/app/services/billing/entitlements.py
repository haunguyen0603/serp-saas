from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.keyword import Keyword
from app.models.project import Project
from app.services.billing.subscriptions import SubscriptionService


class EntitlementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.subscriptions = SubscriptionService(session)

    async def expansion(
        self, user_id: UUID, device: str, projects: int = 0, keywords: int = 0
    ) -> None:
        sub = await self.subscriptions.resolve(user_id, device)
        project_count, keyword_count = await self.subscriptions.repo.counts(
            user_id, device
        )
        if (projects or keywords) and project_count + projects > sub.snapshot[
            "max_projects"
        ]:
            raise AppError(
                409,
                "PROJECT_LIMIT_EXCEEDED",
                "Project limit reached for this device. "
                "Archive Projects or contact an administrator.",
            )
        if (projects or keywords) and keyword_count + keywords > sub.snapshot[
            "max_keywords"
        ]:
            raise AppError(
                409,
                "KEYWORD_LIMIT_EXCEEDED",
                "Keyword limit reached for this device. "
                "Pause Keywords or contact an administrator.",
            )

    async def keyword_add(
        self, user_id: UUID, project_id: UUID, normalized: list[str]
    ) -> None:
        await self.subscriptions.repo.lock(user_id)
        project = await self.session.get(Project, project_id, populate_existing=True)
        if project is None or project.user_id != user_id:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        existing = set(
            await self.session.scalars(
                select(Keyword.keyword_normalized).where(
                    Keyword.project_id == project_id,
                    Keyword.keyword_normalized.in_(normalized),
                )
            )
        )
        if project.status == "active":
            await self.expansion(
                user_id, project.device, keywords=len(set(normalized) - existing)
            )

    async def project_change(
        self, user_id: UUID, project_id: UUID, device: str | None, status: str | None
    ) -> None:
        await self.subscriptions.repo.lock(user_id)
        project = await self.session.get(Project, project_id, populate_existing=True)
        if project is None or project.user_id != user_id:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        target = device or project.device
        if (status or project.status) == "active" and (
            project.status != "active" or target != project.device
        ):
            count = await self.session.scalar(
                select(func.count())
                .select_from(Keyword)
                .where(Keyword.project_id == project_id, Keyword.active.is_(True))
            )
            await self.expansion(user_id, target, projects=1, keywords=count or 0)
        if target != project.device:
            from app.models.rank_job import RankCheckJob

            pending = await self.session.scalar(
                select(RankCheckJob.id)
                .where(
                    RankCheckJob.project_id == project_id,
                    RankCheckJob.status.in_(["pending", "queued", "running"]),
                )
                .limit(1)
            )
            if pending:
                raise AppError(
                    409,
                    "PLAN_DEVICE_MISMATCH",
                    "Wait for pending rank checks before changing device.",
                )
            # Validate target entitlement, then disable incompatible existing schedule.
            sub = await self.subscriptions.resolve(user_id, target)
            from app.models.rank_job import ProjectRankSchedule

            schedule = await self.session.scalar(
                select(ProjectRankSchedule).where(
                    ProjectRankSchedule.project_id == project_id,
                    ProjectRankSchedule.enabled.is_(True),
                )
            )
            if schedule and (
                not sub.snapshot["scheduled_checks_enabled"]
                or (
                    schedule.frequency == "daily"
                    and sub.snapshot["max_scheduled_frequency"] != "daily"
                )
            ):
                schedule.enabled = False
                self.subscriptions.audit(
                    user_id,
                    target,
                    "schedule_disabled_due_to_plan",
                    subscription=sub,
                    metadata={"project_id": str(project_id), "reason": "device_change"},
                )

    async def schedule(self, user_id: UUID, device: str, frequency: str) -> None:
        sub = await self.subscriptions.resolve(user_id, device)
        if not sub.snapshot["scheduled_checks_enabled"]:
            raise AppError(
                403,
                "SCHEDULE_NOT_INCLUDED",
                "Scheduled checks are not included in this Plan.",
            )
        if frequency == "daily" and sub.snapshot["max_scheduled_frequency"] != "daily":
            raise AppError(
                403,
                "SCHEDULE_FREQUENCY_NOT_ALLOWED",
                "This Plan allows weekly schedules only.",
            )
