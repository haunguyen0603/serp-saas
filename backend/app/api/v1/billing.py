from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.dependencies.auth import CurrentUser, DBSession
from app.models.user import User
from app.repositories.billing import BillingRepository
from app.schemas.billing import (
    ActivationRequest,
    AdjustmentRequest,
    AdminPlanResponse,
    ExtendRequest,
    PlanChangeResponse,
    PlanResponse,
    PlanUpdateRequest,
    SubscriptionResponse,
)
from app.services.billing.catalog import PlanCatalogService
from app.services.billing.subscriptions import SubscriptionService
from app.services.billing.usage import UsageService
from app.services.billing.views import BillingViewService

router = APIRouter(tags=["billing"])


async def require_admin(user: CurrentUser) -> User:
    if not user.is_platform_admin:
        raise AppError(
            403, "ADMIN_REQUIRED", "Platform administrator access is required."
        )
    return user


Admin = Annotated[User, Depends(require_admin)]


@router.get("/billing/plans")
async def plans(session: DBSession) -> list[PlanResponse]:
    return [
        PlanResponse.model_validate(p) for p in await BillingRepository(session).plans()
    ]


@router.get("/billing/me")
async def me(user: CurrentUser, session: DBSession) -> dict[str, Any]:
    return await BillingViewService(session).summary(user.id)


@router.get("/admin/plans")
async def admin_plans(admin: Admin, session: DBSession) -> list[AdminPlanResponse]:
    return [
        AdminPlanResponse.model_validate(p)
        for p in await BillingRepository(session).plans()
    ]


@router.get("/admin/plans/history")
async def plan_history(admin: Admin, session: DBSession) -> list[PlanChangeResponse]:
    return [
        PlanChangeResponse.model_validate(change)
        for change in await PlanCatalogService(session).history()
    ]


@router.patch("/admin/plans/{code}")
async def update_plan(
    code: str, data: PlanUpdateRequest, admin: Admin, session: DBSession
) -> AdminPlanResponse:
    return AdminPlanResponse.model_validate(
        await PlanCatalogService(session).update(code, admin.id, data)
    )


@router.get("/billing/me/usage")
async def my_usage(user: CurrentUser, session: DBSession) -> dict[str, Any]:
    return await BillingViewService(session).usage(user.id)


@router.get("/admin/customers")
async def customers(
    admin: Admin,
    session: DBSession,
    search: Annotated[str | None, Query(max_length=320)] = None,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    return await BillingViewService(session).customers(search, cursor, limit)


@router.get("/admin/customers/{user_id}/billing")
async def customer(user_id: UUID, admin: Admin, session: DBSession) -> dict[str, Any]:
    return await BillingViewService(session).summary(user_id)


@router.get("/admin/customers/{user_id}/subscriptions")
async def history(
    user_id: UUID, admin: Admin, session: DBSession
) -> list[SubscriptionResponse]:
    return await BillingViewService(session).history(user_id)


@router.post("/admin/customers/{user_id}/subscriptions", status_code=201)
async def activate(
    user_id: UUID, data: ActivationRequest, admin: Admin, session: DBSession
) -> SubscriptionResponse:
    sub = await SubscriptionService(session).activate(
        user_id,
        admin.id,
        data.plan_code,
        data.period_start,
        data.period_end,
        data.payment_method,
        data.payment_reference,
        data.note,
        data.replace_existing,
    )
    return SubscriptionResponse.model_validate(sub)


@router.post("/admin/customers/{user_id}/subscriptions/{subscription_id}/extend")
async def extend(
    user_id: UUID,
    subscription_id: UUID,
    data: ExtendRequest,
    admin: Admin,
    session: DBSession,
) -> SubscriptionResponse:
    return SubscriptionResponse.model_validate(
        await SubscriptionService(session).extend(
            user_id, admin.id, subscription_id, data.period_end
        )
    )


@router.post("/admin/customers/{user_id}/subscriptions/{subscription_id}/cancel")
async def cancel(
    user_id: UUID, subscription_id: UUID, admin: Admin, session: DBSession
) -> SubscriptionResponse:
    return SubscriptionResponse.model_validate(
        await SubscriptionService(session).cancel(user_id, admin.id, subscription_id)
    )


@router.get("/admin/customers/{user_id}/usage")
async def usage(user_id: UUID, admin: Admin, session: DBSession) -> dict[str, Any]:
    return await BillingViewService(session).usage(user_id, internal=True)


@router.post("/admin/customers/{user_id}/usage-adjustments")
async def adjust(
    user_id: UUID, data: AdjustmentRequest, admin: Admin, session: DBSession
) -> dict[str, Any]:
    await UsageService(session).adjust(
        user_id, admin.id, data.device_scope, data.amount, data.note
    )
    return await BillingViewService(session).summary(user_id)
