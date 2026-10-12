"""Deterministic provider protocol fixtures; no network or merchant credentials."""

import base64
import hashlib
import hmac
from itertools import product

import pytest

from app.core.config import Settings
from app.services.payments.sepay import SIGNED_FIELDS, SePayCheckoutSigner, exact_amount


@pytest.mark.parametrize("customer,method", list(product([False, True], repeat=2)))
def test_signature_documented_order(customer, method):
    fields = {
        "order_amount": "100000",
        "merchant": "TEST-MERCHANT",
        "currency": "VND",
        "operation": "PURCHASE",
        "order_description": "Thanh toán đơn hàng #12345",
        "order_invoice_number": "INV_TEST_001",
        "success_url": "https://app.example.test/success?a=1&b=2",
        "error_url": "https://app.example.test/error",
        "cancel_url": "https://app.example.test/cancel",
    }
    if customer:
        fields["customer_id"] = "test-user"
    if method:
        fields["payment_method"] = "CARD"
    message = (
        "order_amount=100000,merchant=TEST-MERCHANT,currency=VND,operation=PURCHASE,"
        "order_description=Thanh toán đơn hàng #12345,"
        "order_invoice_number=INV_TEST_001,"
        + ("customer_id=test-user," if customer else "")
        + ("payment_method=CARD," if method else "")
        + "success_url=https://app.example.test/success?a=1&b=2,"
        "error_url=https://app.example.test/error,cancel_url=https://app.example.test/cancel"
    )
    expected = base64.b64encode(
        hmac.digest(b"test-only-signing-key", message.encode(), "sha256")
    ).decode()
    actual = SePayCheckoutSigner.sign(
        dict(reversed(list(fields.items()))), "test-only-signing-key"
    )
    assert actual == expected
    sorted_message = ",".join(f"{key}={fields[key]}" for key in sorted(fields))
    assert (
        actual
        != base64.b64encode(
            hmac.new(
                b"test-only-signing-key", sorted_message.encode(), hashlib.sha256
            ).digest()
        ).decode()
    )
    assert len(base64.b64decode(actual)) == 32
    assert SIGNED_FIELDS[0] == "order_amount"
    if not customer and not method:
        assert actual == "/FM9RaKdUKoLxedrRQzzKAZ87z/fX0SeVogrlBHAido="


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("100000.00", 100000),
        ("100000", 100000),
        (100000, 100000),
        (100000.0, None),
        ("100000.01", None),
        (True, None),
        ("NaN", None),
        ("Infinity", None),
        ("1e999999", None),
        ("0", None),
        ("-1", None),
        (None, None),
        ({}, None),
    ],
)
def test_exact_money(raw, expected):
    assert exact_amount(raw) == expected


def test_enabled_config_requires_explicit_https_and_secrets(settings):
    with pytest.raises(ValueError):
        Settings(**{**settings.model_dump(), "sepay_enabled": True})
    assert (
        "sepay_secret_key" not in repr(settings)
        or "**********" in repr(settings)
        or settings.sepay_secret_key is None
    )
