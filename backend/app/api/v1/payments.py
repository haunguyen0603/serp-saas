from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header

from app.dependencies.auth import AppSettings, CurrentUser, DBSession
from app.schemas.payment import CheckoutRequest, CheckoutResponse, PaymentStatusResponse
from app.services.payments.sepay import SePayPaymentProvider
from app.services.payments.service import PaymentService

router = APIRouter(prefix="/billing/payments", tags=["payments"])


@router.get("/sepay/options")
async def options(
    user: CurrentUser, session: DBSession, settings: AppSettings
) -> dict[str, Any]:
    return await PaymentService(session, settings).options(user)


@router.post("/sepay/checkout", status_code=201)
async def checkout(
    data: CheckoutRequest, user: CurrentUser, session: DBSession, settings: AppSettings
) -> CheckoutResponse:
    return await PaymentService(session, settings).checkout(user, data)


@router.post("/sepay/ipn")
async def ipn(
    payload: dict[str, Any],
    session: DBSession,
    settings: AppSettings,
    x_secret_key: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    SePayPaymentProvider(settings).verify_ipn(x_secret_key)
    return await PaymentService(session, settings).ipn(payload)


@router.get("/{payment_order_id}")
async def status(
    payment_order_id: UUID, user: CurrentUser, session: DBSession, settings: AppSettings
) -> PaymentStatusResponse:
    return PaymentStatusResponse.model_validate(
        await PaymentService(session, settings).status(user.id, payment_order_id)
    )
