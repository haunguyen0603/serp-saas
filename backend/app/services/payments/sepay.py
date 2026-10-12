import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from app.core.config import Settings
from app.core.errors import AppError
from app.models.payment import PaymentOrder

SIGNED_FIELDS = (
    "order_amount",
    "merchant",
    "currency",
    "operation",
    "order_description",
    "order_invoice_number",
    "customer_id",
    "payment_method",
    "success_url",
    "error_url",
    "cancel_url",
)


class SePayCheckoutSigner:
    @staticmethod
    def sign(fields: dict[str, str], secret: str) -> str:
        message = ",".join(
            f"{key}={fields[key]}" for key in SIGNED_FIELDS if key in fields
        )
        return base64.b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode("ascii")


def callback_url(url: str, order_id: UUID) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "payment_order_id"]
    query.append(("payment_order_id", str(order_id)))
    return urlunsplit(parts._replace(query=urlencode(query)))


def exact_amount(value: Any) -> int | None:
    # JSON floating point and booleans are deliberately not payment evidence.
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    if isinstance(value, str) and len(value) > 64:
        return None
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount != amount.to_integral_value():
            return None
        if amount <= 0 or amount > 2147483647:
            return None
        return int(amount)
    except (InvalidOperation, ValueError):
        return None


@dataclass(frozen=True)
class ProviderEvent:
    notification_type: str
    invoice: str
    order: dict[str, Any]
    transaction: dict[str, Any]
    safe_payload: dict[str, Any]
    event_key: str


class PaymentProvider(Protocol):
    @property
    def available(self) -> bool: ...

    def create_checkout(self, order: PaymentOrder) -> dict[str, str]: ...
    def verify_ipn(self, secret: str | None) -> None: ...
    def normalize_event(self, payload: dict[str, Any]) -> ProviderEvent: ...


class SePayPaymentProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return self.settings.sepay_enabled

    def create_checkout(self, order: PaymentOrder) -> dict[str, str]:
        if not self.available or not self.settings.sepay_secret_key:
            raise AppError(
                503, "PAYMENT_CHECKOUT_UNAVAILABLE", "Checkout is unavailable."
            )
        fields = {
            "order_amount": str(order.amount_minor),
            "merchant": self.settings.sepay_merchant_id,
            "currency": order.currency,
            "operation": "PURCHASE",
            "order_description": f"{order.plan_name_snapshot} — 1 month",
            "order_invoice_number": order.invoice_number,
            "customer_id": str(order.user_id),
            "success_url": callback_url(self.settings.sepay_success_url, order.id),
            "error_url": callback_url(self.settings.sepay_error_url, order.id),
            "cancel_url": callback_url(self.settings.sepay_cancel_url, order.id),
        }
        fields["signature"] = SePayCheckoutSigner.sign(
            fields, self.settings.sepay_secret_key.get_secret_value()
        )
        return fields

    def verify_ipn(self, secret: str | None) -> None:
        expected = self.settings.sepay_ipn_secret_key
        if (
            not expected
            or not expected.get_secret_value()
            or not secret
            or not (
                hmac.compare_digest(
                    secret.encode(), expected.get_secret_value().encode()
                )
            )
        ):
            logging.getLogger(__name__).warning("payment_ipn_rejected")
            raise AppError(
                401, "PAYMENT_PROVIDER_AUTH_FAILED", "Invalid provider authentication."
            )
        logging.getLogger(__name__).info("payment_ipn_authenticated")

    def normalize_event(self, payload: dict[str, Any]) -> ProviderEvent:
        kind = payload.get("notification_type")
        order, transaction = payload.get("order"), payload.get("transaction")
        if (
            not isinstance(kind, str)
            or not 0 < len(kind) <= 64
            or not isinstance(order, dict)
            or not isinstance(transaction, dict)
        ):
            raise AppError(
                422, "PAYMENT_PROVIDER_EVENT_INVALID", "Invalid payment event."
            )

        # Store financial evidence only; drop personal and card data.
        def minimize(data: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
            return {
                key: data[key]
                for key in keys
                if key in data
                and isinstance(data[key], (str, int))
                and not isinstance(data[key], bool)
                and len(str(data[key])) <= 200
            }

        safe_order = minimize(
            order,
            (
                "id",
                "order_id",
                "order_invoice_number",
                "order_status",
                "order_currency",
                "order_amount",
            ),
        )
        safe_transaction = minimize(
            transaction,
            (
                "id",
                "transaction_id",
                "transaction_type",
                "transaction_status",
                "transaction_currency",
                "transaction_amount",
                "payment_method",
            ),
        )
        invoice = safe_order.get("order_invoice_number")
        if not isinstance(invoice, str) or not invoice:
            raise AppError(
                422, "PAYMENT_PROVIDER_EVENT_INVALID", "Missing invoice number."
            )
        safe = {
            "notification_type": kind,
            "order": safe_order,
            "transaction": safe_transaction,
        }
        # Retry timestamps and personal data do not change event identity.
        event_key = hashlib.sha256(
            (self.settings.sepay_env + json.dumps(safe, sort_keys=True)).encode()
        ).hexdigest()
        return ProviderEvent(
            kind, invoice, safe_order, safe_transaction, safe, event_key
        )
