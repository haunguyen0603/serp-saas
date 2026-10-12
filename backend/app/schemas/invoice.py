from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

InvoiceStatus = Literal[
    "pending",
    "checkout_created",
    "paid",
    "failed",
    "cancelled",
    "voided",
    "expired",
    "review_required",
]


class InvoiceSummary(BaseModel):
    id: UUID
    invoice_number: str
    status: InvoiceStatus
    product_line: Literal["desktop", "mobile"]
    plan_code: str
    plan_name: str
    amount_minor: int
    currency: str
    provider: str
    provider_environment: Literal["sandbox", "production"]
    created_at: datetime
    paid_at: datetime | None


class InvoiceTerms(BaseModel):
    billing_months: int | None = None
    max_projects: int | None = None
    max_keywords: int | None = None
    monthly_keyword_checks: int | None = None
    scheduled_checks_enabled: bool | None = None
    max_scheduled_frequency: str | None = None


class InvoiceDetail(InvoiceSummary):
    account_email: str
    payment_method: str | None
    provider_order_id: str | None
    provider_transaction_id: str | None
    provider_transaction_uuid: str | None
    updated_at: datetime
    expires_at: datetime
    cancelled_at: datetime | None
    failed_at: datetime | None
    terms: InvoiceTerms


class InvoiceList(BaseModel):
    items: list[InvoiceSummary]
    next_cursor: str | None
    has_more: bool
