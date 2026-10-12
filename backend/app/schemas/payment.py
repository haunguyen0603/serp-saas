from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: UUID
    product_line: Literal["desktop", "mobile"]


class CheckoutResponse(BaseModel):
    payment_order_id: UUID
    invoice_number: str
    checkout_url: str
    form: dict[str, str]


class PaymentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_number: str
    status: str
    product_line: str
    plan_code: str
    plan_name_snapshot: str
    amount_minor: int
    currency: str
    created_at: datetime
    paid_at: datetime | None
    subscription_id: UUID | None
