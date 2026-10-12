from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from app.models.billing import Plan, Subscription
from app.models.payment import PaymentOrder
from tests.business_helpers import authorization, register
from tests.test_auth import auth_app, auth_client
from tests.test_payments import account, checkout, paid, payment_config, send

__all__ = ["auth_app", "auth_client", "payment_config"]
pytestmark = pytest.mark.integration
BASE = "/api/v1/billing/invoices"


async def test_invoice_ownership_auth_and_private_download(auth_client, auth_app):
    headers, _ = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    own_id = body["payment_order_id"]
    other, _ = await account(auth_client, auth_app)
    for suffix in ("", f"/{own_id}", f"/{own_id}/pdf"):
        assert (await auth_client.get(BASE + suffix)).status_code == 401
    assert (await auth_client.get(BASE, headers=other)).json()["items"] == []
    for suffix in (f"/{own_id}", f"/{own_id}/pdf", f"/{uuid4()}"):
        assert (await auth_client.get(BASE + suffix, headers=other)).status_code == 404
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"auth_require_verified_email": True}
    )
    unverified = authorization(await register(auth_client))
    for suffix in ("", f"/{own_id}", f"/{own_id}/pdf"):
        assert (
            await auth_client.get(BASE + suffix, headers=unverified)
        ).status_code == 403
    for suffix in ("", f"/{own_id}", f"/{own_id}/pdf"):
        response = await auth_client.get(BASE + suffix, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="invoice-{body["invoice_number"]}.pdf"'
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 5000


async def test_invoice_cursor_filters_and_read_only_expiry(auth_client, auth_app):
    headers, uid = await account(auth_client, auth_app)
    orders = [(await checkout(auth_client, headers)).json() for _ in range(3)]
    mobile = (await checkout(auth_client, headers, "mobile_starter")).json()
    stamp = datetime.now(UTC) - timedelta(days=2)
    async with auth_app.state.session_factory() as session, session.begin():
        await session.execute(
            update(PaymentOrder)
            .where(PaymentOrder.user_id == uid)
            .values(created_at=stamp)
        )
        first = await session.get(PaymentOrder, UUID(orders[0]["payment_order_id"]))
        first.expires_at = stamp
        second = await session.get(PaymentOrder, UUID(orders[1]["payment_order_id"]))
        second.status = "failed"
        second.provider_environment = "production"
    expected = sorted([o["payment_order_id"] for o in [*orders, mobile]], reverse=True)
    found = []
    cursor = None
    for _ in range(2):
        response = await auth_client.get(
            BASE,
            headers=headers,
            params={"limit": 2, **({"cursor": cursor} if cursor else {})},
        )
        page = response.json()
        found.extend(i["id"] for i in page["items"])
        cursor = page["next_cursor"]
    assert found == expected
    assert not page["has_more"] and cursor is None
    expired = (
        await auth_client.get(BASE, headers=headers, params={"status": "expired"})
    ).json()
    assert [i["id"] for i in expired["items"]] == [orders[0]["payment_order_id"]]
    detail = (
        await auth_client.get(
            f"{BASE}/{orders[0]['payment_order_id']}", headers=headers
        )
    ).json()
    assert detail["status"] == "expired"
    active = (
        await auth_client.get(
            BASE, headers=headers, params={"status": "checkout_created"}
        )
    ).json()
    assert len(active["items"]) == 2
    filtered = (
        await auth_client.get(
            BASE,
            headers=headers,
            params={
                "product_line": "desktop",
                "environment": "production",
                "status": "failed",
            },
        )
    ).json()
    assert [i["id"] for i in filtered["items"]] == [orders[1]["payment_order_id"]]
    async with auth_app.state.session_factory() as session:
        order = await session.get(PaymentOrder, UUID(orders[0]["payment_order_id"]))
        assert (
            order.status == "checkout_created"
        )  # Listing/export never changes payment state.
    for params in (
        {"cursor": "invalid"},
        {"limit": 0},
        {"limit": 101},
        {"status": "refunded"},
        {"product_line": "other"},
        {"environment": "other"},
    ):
        assert (
            await auth_client.get(BASE, headers=headers, params=params)
        ).status_code == 422


async def test_invoice_paid_snapshot_redaction_and_gateway_disabled(
    auth_client, auth_app
):
    headers, uid = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    assert (await send(auth_client, paid(body))).status_code == 200
    invoice_id = UUID(body["payment_order_id"])
    async with auth_app.state.session_factory() as session, session.begin():
        order = await session.get(PaymentOrder, invoice_id)
        await session.execute(
            update(Plan)
            .where(Plan.id == order.plan_id)
            .values(
                name="New price name", max_projects=99, price_monthly_minor_units=999999
            )
        )
        order.provider_payload_snapshot = {
            "card_number": "DO-NOT-EXPOSE",
            "secret": "DO-NOT-EXPOSE",
        }
        order.commercial_snapshot = {
            **order.commercial_snapshot,
            "secret": "DO-NOT-EXPOSE",
        }
        before = (order.status, order.subscription_id, order.paid_at)
        subscriptions = list(
            await session.scalars(
                select(Subscription).where(Subscription.user_id == uid)
            )
        )
        periods = [(s.id, s.period_start, s.period_end) for s in subscriptions]
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"sepay_enabled": False}
    )
    response = await auth_client.get(f"{BASE}/{invoice_id}", headers=headers)
    assert response.status_code == 200
    detail = response.json()
    assert detail["status"] == "paid"
    assert detail["amount_minor"] == 495330 and detail["currency"] == "VND"
    assert detail["plan_name"] == "Desktop Starter"
    assert detail["terms"]["max_projects"] == 5
    assert detail["terms"]["billing_months"] == 1
    assert detail["provider_environment"] == "sandbox"
    assert detail["payment_method"] == "CARD"
    assert detail["provider_transaction_id"] and detail["paid_at"]
    assert "DO-NOT-EXPOSE" not in response.text
    assert "secret" not in detail["terms"] and "provider_payload_snapshot" not in detail
    assert (
        await auth_client.get(f"{BASE}/{invoice_id}/pdf", headers=headers)
    ).status_code == 200
    async with auth_app.state.session_factory() as session:
        order = await session.get(PaymentOrder, invoice_id)
        assert (order.status, order.subscription_id, order.paid_at) == before
        subscriptions = list(
            await session.scalars(
                select(Subscription).where(Subscription.user_id == uid)
            )
        )
        assert [(s.id, s.period_start, s.period_end) for s in subscriptions] == periods
