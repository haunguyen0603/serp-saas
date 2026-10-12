import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.billing import Plan, Subscription
from app.models.payment import PaymentOrder
from app.models.user import User
from app.repositories.billing import BillingRepository
from app.repositories.payment import PaymentEventRepository, PaymentOrderRepository
from app.schemas.payment import CheckoutRequest, CheckoutResponse
from app.services.billing.currency import replacement_event
from app.services.billing.subscriptions import TERMS, SubscriptionService, snapshot
from app.services.payments.sepay import (
    PaymentProvider,
    ProviderEvent,
    SePayPaymentProvider,
    exact_amount,
)

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings
        self.provider: PaymentProvider = SePayPaymentProvider(settings)
        self.orders = PaymentOrderRepository(session)
        self.events = PaymentEventRepository(session)
        self.billing = BillingRepository(session)
        self.subscriptions = SubscriptionService(session)

    async def transition(
        self, user_id: UUID, plan_id: UUID, terms: dict[str, Any]
    ) -> None:
        current = await self.subscriptions.resolve(user_id, terms["device_scope"])
        scheduled = await self.session.scalar(
            select(Subscription.id)
            .where(
                Subscription.user_id == user_id,
                Subscription.device_scope == terms["device_scope"],
                Subscription.status == "scheduled",
            )
            .limit(1)
        )
        if scheduled:
            raise AppError(
                409,
                "PAYMENT_TRANSITION_NOT_ALLOWED",
                "Contact support to change a scheduled subscription.",
            )
        if (
            current.plan_id != plan_id
            and replacement_event(
                Plan(**{key: terms[key] for key in TERMS}), current.snapshot
            )
            == "subscription_downgraded"
        ):
            raise AppError(
                409,
                "PAYMENT_TRANSITION_NOT_ALLOWED",
                "Paid downgrades are unavailable. Contact support.",
            )

    def sandbox_customer_allowed(self, user: User) -> bool:
        return (
            self.settings.app_env != "production"
            or self.settings.sepay_env != "sandbox"
            or user.is_platform_admin
            or user.id in self.settings.sepay_sandbox_allowed_user_ids
        )

    async def options(self, user: User) -> dict[str, Any]:
        if (
            not self.provider.available
            or user.email_verified_at is None
            or not self.sandbox_customer_allowed(user)
        ):
            return {"enabled": False, "eligible_plan_ids": []}
        eligible = []
        for plan in await self.billing.plans():
            if plan.currency != "VND" or plan.price_monthly_minor_units <= 0:
                continue
            try:
                await self.transition(user.id, plan.id, snapshot(plan))
            except AppError as error:
                if error.code not in (
                    "PAYMENT_TRANSITION_NOT_ALLOWED",
                    "PLAN_CURRENCY_MISMATCH",
                ):
                    raise
                continue
            eligible.append(str(plan.id))
        return {"enabled": True, "eligible_plan_ids": eligible}

    async def checkout(self, user: User, data: CheckoutRequest) -> CheckoutResponse:
        if user.email_verified_at is None:
            raise AppError(
                403, "EMAIL_NOT_VERIFIED", "Verify your email before payment."
            )
        if not self.provider.available or not self.sandbox_customer_allowed(user):
            raise AppError(
                503, "PAYMENT_CHECKOUT_UNAVAILABLE", "Checkout is unavailable."
            )
        plan = await self.session.get(Plan, data.plan_id)
        if plan is None:
            raise AppError(404, "PAYMENT_PLAN_NOT_FOUND", "Plan not found.")
        if not plan.active or plan.price_monthly_minor_units == 0:
            raise AppError(
                422, "PAYMENT_PLAN_NOT_PURCHASABLE", "Select an active paid plan."
            )
        if plan.device_scope != data.product_line:
            raise AppError(
                422,
                "PAYMENT_TRANSITION_NOT_ALLOWED",
                "Plan product line does not match.",
            )
        if plan.currency != "VND":
            raise AppError(
                422, "PAYMENT_CURRENCY_UNSUPPORTED", "Checkout requires VND pricing."
            )
        if exact_amount(plan.price_monthly_minor_units) is None:
            raise AppError(422, "PAYMENT_AMOUNT_INVALID", "Invalid checkout amount.")
        await self.transition(user.id, plan.id, snapshot(plan))
        now = datetime.now(UTC)
        await self.session.execute(
            update(PaymentOrder)
            .where(
                PaymentOrder.user_id == user.id,
                PaymentOrder.status.in_(["pending", "checkout_created"]),
                PaymentOrder.expires_at <= now,
            )
            .values(status="expired")
        )
        order = PaymentOrder(
            id=uuid4(),
            user_id=user.id,
            provider="sepay",
            provider_environment=self.settings.sepay_env,
            invoice_number=f"PAY_{uuid4().hex.upper()}",
            product_line=plan.device_scope,
            plan_id=plan.id,
            plan_code=plan.code,
            plan_name_snapshot=plan.name,
            currency=plan.currency,
            amount_minor=plan.price_monthly_minor_units,
            commercial_snapshot={**snapshot(plan), "billing_months": 1},
            status="pending",
            expires_at=now + timedelta(minutes=self.settings.sepay_pending_minutes),
        )
        self.session.add(order)
        await self.session.flush()
        fields = self.provider.create_checkout(order)
        order.status = "checkout_created"
        logger.info(
            "payment_checkout_created", extra={"payment_order_id": str(order.id)}
        )
        return CheckoutResponse(
            payment_order_id=order.id,
            invoice_number=order.invoice_number,
            checkout_url=self.settings.sepay_checkout_url,
            form=fields,
        )

    async def status(self, user_id: UUID, order_id: UUID) -> PaymentOrder:
        await self.billing.lock(user_id)
        order = await self.orders.owned(order_id, user_id)
        if order is None:
            raise AppError(404, "PAYMENT_ORDER_NOT_FOUND", "Payment order not found.")
        if order.status in (
            "pending",
            "checkout_created",
        ) and order.expires_at <= datetime.now(UTC):
            order.status = "expired"
        return order

    def validation_error(self, order: PaymentOrder, event: ProviderEvent) -> str | None:
        po, tx = event.order, event.transaction
        if order.provider_environment != self.settings.sepay_env:
            return "PAYMENT_PROVIDER_ENVIRONMENT_MISMATCH"
        if not all(
            isinstance(data.get(key), str) and data[key]
            for data, key in (
                (po, "id"),
                (tx, "id"),
                (tx, "transaction_id"),
            )
        ):
            return "PAYMENT_PROVIDER_EVENT_INVALID"
        if (
            po.get("order_currency") != order.currency
            or tx.get("transaction_currency") != order.currency
        ):
            return "PAYMENT_CURRENCY_MISMATCH"
        if (
            exact_amount(po.get("order_amount")) != order.amount_minor
            or exact_amount(tx.get("transaction_amount")) != order.amount_minor
        ):
            return "PAYMENT_AMOUNT_MISMATCH"
        if event.notification_type == "ORDER_PAID" and (
            po.get("order_status") != "CAPTURED"
            or tx.get("transaction_status") != "APPROVED"
            or tx.get("transaction_type") != "PAYMENT"
        ):
            return "PAYMENT_PROVIDER_EVENT_INVALID"
        if order.provider_order_id and po["id"] != order.provider_order_id:
            return "PAYMENT_PROVIDER_CONFLICT"
        if event.notification_type == "ORDER_PAID" and (
            (
                order.provider_transaction_id
                and tx["transaction_id"] != order.provider_transaction_id
            )
            or (
                order.provider_transaction_uuid
                and tx["id"] != order.provider_transaction_uuid
            )
        ):
            return "PAYMENT_PROVIDER_CONFLICT"
        return None

    async def ipn(self, payload: dict[str, Any]) -> dict[str, bool]:
        event = self.provider.normalize_event(payload)
        await self.orders.lock_transactions(self.settings.sepay_env, event)
        order = await self.orders.invoice(event.invoice)
        # Match billing's user-lock-before-row ordering in every mutation path.
        if order:
            await self.billing.lock(order.user_id)
            order = await self.orders.invoice(event.invoice, lock=True)
        stored = await self.events.record(event, order.id if order else None)
        if stored is None:
            logger.info("payment_duplicate_event")
            return {"success": True}
        now = datetime.now(UTC)
        result = "ignored_notification"
        error = None
        if event.notification_type not in ("ORDER_PAID", "TRANSACTION_VOID"):
            pass
        elif order is None:
            result = "PAYMENT_ORDER_NOT_FOUND"
        else:
            error = self.validation_error(order, event)
            if not error and await self.orders.transaction_conflict(order, event):
                error = "PAYMENT_PROVIDER_CONFLICT"
            if not error and event.notification_type == "TRANSACTION_VOID":
                # Subscription reversal semantics require operator review.
                error = "PAYMENT_VOID_REVIEW_REQUIRED"
            if not error and not order.subscription_id:
                if (
                    order.status not in ("pending", "checkout_created")
                    or order.expires_at <= now
                ):
                    error = "PAYMENT_LATE_OR_REVIEW_REQUIRED"
                elif not self.valid_snapshot(order):
                    error = "PAYMENT_SNAPSHOT_INVALID"
                else:
                    try:
                        await self.transition(
                            order.user_id, order.plan_id, order.commercial_snapshot
                        )
                    except AppError as exc:
                        if exc.code not in (
                            "PAYMENT_TRANSITION_NOT_ALLOWED",
                            "PLAN_CURRENCY_MISMATCH",
                        ):
                            raise
                        error = exc.code
            if error:
                order.status, order.failure_code = "review_required", error
                result = error
                logger.warning(
                    "payment_reconciliation_required",
                    extra={"payment_order_id": str(order.id), "safe_error_code": error},
                )
            elif order.subscription_id:
                result = "already_activated"
            else:
                # Financial and subscription changes share get_db's transaction.
                terms = {key: order.commercial_snapshot[key] for key in TERMS}
                sub = await self.subscriptions.activate_from_payment(
                    order.user_id,
                    order.plan_id,
                    terms,
                    order.invoice_number,
                    event.transaction.get("payment_method"),
                    now,
                )
                order.subscription_id = sub.id
                order.status, order.paid_at = "paid", now
                order.provider_order_id = event.order["id"]
                order.provider_transaction_id = event.transaction["transaction_id"]
                order.provider_transaction_uuid = event.transaction["id"]
                order.payment_method = event.transaction.get("payment_method")
                order.provider_order_status = event.order.get("order_status")
                order.provider_transaction_status = event.transaction.get(
                    "transaction_status"
                )
                order.provider_payload_snapshot = event.safe_payload
                result = "paid"
                logger.info("payment_paid", extra={"payment_order_id": str(order.id)})
        stored.processing_result, stored.processed_at = result, now
        await self.session.flush()
        return {"success": True}

    @staticmethod
    def valid_snapshot(order: PaymentOrder) -> bool:
        terms = order.commercial_snapshot
        return (
            all(key in terms for key in TERMS)
            and terms.get("code") == order.plan_code
            and terms.get("name") == order.plan_name_snapshot
            and terms.get("device_scope") == order.product_line
            and terms.get("currency") == order.currency
            and type(terms.get("price_monthly_minor_units")) is int
            and terms.get("price_monthly_minor_units") == order.amount_minor
            and type(terms.get("billing_months")) is int
            and terms.get("billing_months") == 1
            and all(
                type(terms.get(key)) is int and 0 <= terms[key] <= 2147483647
                for key in ("max_projects", "max_keywords", "monthly_keyword_checks")
            )
            and type(terms.get("scheduled_checks_enabled")) is bool
            and terms.get("max_scheduled_frequency") in ("none", "weekly", "daily")
        )
