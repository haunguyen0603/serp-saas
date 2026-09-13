from uuid import UUID

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import Plan
from app.models.keyword import Keyword
from app.models.project import Project
from app.models.user import User
from app.services.normalization import decode_cursor


class BillingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock(self, user_id: UUID) -> None:
        # Transaction-scoped advisory lock avoids conflicting with auth FK reads.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(user_id.bytes[:8], "big", signed=True)},
        )

    async def user(self, user_id: UUID) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise AppError(404, "USER_NOT_FOUND", "Customer not found.")
        return user

    async def plan(self, code: str) -> Plan:
        plan = await self.session.scalar(
            select(Plan).where(Plan.code == code, Plan.active.is_(True))
        )
        if plan is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Active Plan not found.")
        return plan

    async def plans(self) -> list[Plan]:
        return list(
            await self.session.scalars(
                select(Plan)
                .where(Plan.active.is_(True))
                .order_by(Plan.device_scope, Plan.display_order)
            )
        )

    async def counts(self, user_id: UUID, device: str) -> tuple[int, int]:
        filters = (
            Project.user_id == user_id,
            Project.device == device,
            Project.status == "active",
        )
        projects = await self.session.scalar(
            select(func.count()).select_from(Project).where(*filters)
        )
        keywords = await self.session.scalar(
            select(func.count())
            .select_from(Keyword)
            .join(Project)
            .where(*filters, Keyword.active.is_(True))
        )
        return projects or 0, keywords or 0

    async def customers(
        self, search: str | None, cursor: str | None, limit: int
    ) -> list[User]:
        statement = select(User)
        if search:
            statement = statement.where(
                User.email.contains(search.strip().lower(), autoescape=True)
            )
        if cursor:
            statement = statement.where(
                tuple_(User.created_at, User.id) < decode_cursor(cursor)
            )
        return list(
            await self.session.scalars(
                statement.order_by(User.created_at.desc(), User.id.desc()).limit(
                    limit + 1
                )
            )
        )
