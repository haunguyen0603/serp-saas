from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.payment import PaymentOrder
from app.models.user import User
from app.repositories.payment import PaymentOrderRepository
from app.schemas.invoice import (
    InvoiceDetail,
    InvoiceList,
    InvoiceStatus,
    InvoiceSummary,
    InvoiceTerms,
)
from app.services.normalization import decode_cursor, encode_cursor


def summary(order: PaymentOrder, now: datetime) -> InvoiceSummary:
    status = order.status
    if status in {"pending", "checkout_created"} and order.expires_at <= now:
        status = "expired"
    return InvoiceSummary.model_validate(
        {
            "id": order.id,
            "invoice_number": order.invoice_number,
            "status": status,
            "product_line": order.product_line,
            "plan_code": order.plan_code,
            "plan_name": order.plan_name_snapshot,
            "amount_minor": order.amount_minor,
            "currency": order.currency,
            "provider": order.provider,
            "provider_environment": order.provider_environment,
            "created_at": order.created_at,
            "paid_at": order.paid_at,
        }
    )


class InvoiceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_owned(
        self,
        user_id: UUID,
        *,
        limit: int,
        cursor: str | None,
        status: InvoiceStatus | None,
        product_line: str | None,
        environment: str | None,
    ) -> InvoiceList:
        now = datetime.now(UTC)
        query = select(PaymentOrder).where(PaymentOrder.user_id == user_id)
        if status:
            effective_status = case(
                (
                    PaymentOrder.status.in_(["pending", "checkout_created"])
                    & (PaymentOrder.expires_at <= now),
                    "expired",
                ),
                else_=PaymentOrder.status,
            )
            query = query.where(effective_status == status)
        if product_line:
            query = query.where(PaymentOrder.product_line == product_line)
        if environment:
            query = query.where(PaymentOrder.provider_environment == environment)
        boundary = decode_cursor(cursor)
        if boundary:
            query = query.where(
                tuple_(PaymentOrder.created_at, PaymentOrder.id) < boundary
            )
        orders = list(
            await self.session.scalars(
                query.order_by(
                    PaymentOrder.created_at.desc(), PaymentOrder.id.desc()
                ).limit(limit + 1)
            )
        )
        more = len(orders) > limit
        visible = orders[:limit]
        return InvoiceList(
            items=[summary(order, now) for order in visible],
            has_more=more,
            next_cursor=(
                encode_cursor(visible[-1].created_at, visible[-1].id) if more else None
            ),
        )

    async def detail(self, user: User, invoice_id: UUID) -> InvoiceDetail:
        order = await PaymentOrderRepository(self.session).owned(invoice_id, user.id)
        if order is None:
            raise AppError(404, "INVOICE_NOT_FOUND", "Invoice not found.")
        # Export only explicit customer fields; never provider payloads or secrets.
        return InvoiceDetail(
            **summary(order, datetime.now(UTC)).model_dump(),
            account_email=user.email,
            payment_method=order.payment_method,
            provider_order_id=order.provider_order_id,
            provider_transaction_id=order.provider_transaction_id,
            provider_transaction_uuid=order.provider_transaction_uuid,
            updated_at=order.updated_at,
            expires_at=order.expires_at,
            cancelled_at=order.cancelled_at,
            failed_at=order.failed_at,
            terms=InvoiceTerms.model_validate(order.commercial_snapshot),
        )
