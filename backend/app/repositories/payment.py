import hashlib
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentEvent, PaymentOrder
from app.services.payments.sepay import ProviderEvent


class PaymentOrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def owned(self, order_id: UUID, user_id: UUID) -> PaymentOrder | None:
        return cast(
            PaymentOrder | None,
            await self.session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.id == order_id, PaymentOrder.user_id == user_id
                )
            ),
        )

    async def invoice(self, invoice: str, *, lock: bool = False) -> PaymentOrder | None:
        query = select(PaymentOrder).where(PaymentOrder.invoice_number == invoice)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return cast(PaymentOrder | None, await self.session.scalar(query))

    async def lock_transactions(self, environment: str, event: ProviderEvent) -> None:
        keys = sorted(
            {
                str(event.transaction[key])
                for key in ("id", "transaction_id")
                if event.transaction.get(key)
            }
        )
        if event.order.get("id"):
            keys.append(str(event.order["id"]))
        for key in sorted(set(keys)):
            digest = hashlib.sha256(f"sepay:{environment}:{key}".encode()).digest()
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": int.from_bytes(digest[:8], "big", signed=True)},
            )

    async def transaction_conflict(
        self, order: PaymentOrder, event: ProviderEvent
    ) -> bool:
        ids = [
            str(event.transaction[key])
            for key in ("id", "transaction_id")
            if event.transaction.get(key)
        ]
        return bool(
            await self.session.scalar(
                select(PaymentOrder.id)
                .where(
                    PaymentOrder.id != order.id,
                    PaymentOrder.provider == "sepay",
                    PaymentOrder.provider_environment == order.provider_environment,
                    or_(
                        PaymentOrder.provider_transaction_id.in_(ids),
                        PaymentOrder.provider_transaction_uuid.in_(ids),
                        PaymentOrder.provider_order_id == event.order.get("id"),
                    ),
                )
                .limit(1)
            )
        )


class PaymentEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self, event: ProviderEvent, order_id: UUID | None
    ) -> PaymentEvent | None:
        now = datetime.now(UTC)
        event_id = await self.session.scalar(
            insert(PaymentEvent)
            .values(
                id=uuid4(),
                provider="sepay",
                event_key=event.event_key,
                notification_type=event.notification_type,
                payment_order_id=order_id,
                raw_payload=event.safe_payload,
                received_at=now,
                processing_result="received",
            )
            .on_conflict_do_nothing(index_elements=["event_key"])
            .returning(PaymentEvent.id)
        )
        return await self.session.get(PaymentEvent, event_id) if event_id else None
