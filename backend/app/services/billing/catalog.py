from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import Plan, PlanChange
from app.schemas.billing import PlanUpdateRequest
from app.services.billing.subscriptions import snapshot


class PlanCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update(self, code: str, actor: UUID, data: PlanUpdateRequest) -> Plan:
        plan = await self.session.scalar(
            select(Plan)
            .where(Plan.code == code, Plan.active.is_(True))
            .with_for_update()
        )
        if plan is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Active Plan not found.")
        if plan.updated_at != data.expected_updated_at:
            raise AppError(
                409, "PLAN_CHANGED", "This Plan has changed. Reload it before saving."
            )
        if plan.code.endswith("_free") and data.price_monthly_minor_units != 0:
            raise AppError(422, "INVALID_PLAN_PRICE", "Free Plans must remain free.")
        if not plan.code.endswith("_free") and data.price_monthly_minor_units == 0:
            raise AppError(
                422, "INVALID_PLAN_PRICE", "Paid Plans need a positive price."
            )
        before = snapshot(plan)
        for key, value in data.model_dump(exclude={"expected_updated_at"}).items():
            setattr(plan, key, value)
        after = snapshot(plan)
        if before != after:
            plan.updated_at = datetime.now(UTC)
            self.session.add(
                PlanChange(
                    plan_id=plan.id, actor_user_id=actor, before=before, after=after
                )
            )
        await self.session.flush()
        return plan

    async def history(self) -> list[PlanChange]:
        return list(
            await self.session.scalars(
                select(PlanChange)
                .order_by(PlanChange.created_at.desc(), PlanChange.id.desc())
                .limit(20)
            )
        )
