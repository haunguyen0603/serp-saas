"""Run in the backend test image as /app/tests/test_production_acceptance.py.

Uses synthetic credentials and isolated PostgreSQL; never contacts SePay.
"""

from uuid import UUID

import pytest
from app.models.billing import Subscription
from app.models.payment import PaymentOrder
from app.models.user import User
from tests.test_auth import auth_app, auth_client
from tests.test_payments import account, checkout, paid, payment_config, send, status

__all__ = ["auth_app", "auth_client", "payment_config"]
pytestmark = pytest.mark.integration


async def test_live_gateway_customer_payment_and_environment_isolation(
    auth_client, auth_app
):
    headers, uid = await account(auth_client, auth_app)
    sandbox_order = (await checkout(auth_client, headers)).json()
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={
            "app_env": "production",
            "sepay_env": "production",
            "sepay_checkout_url": "https://pay.sepay.vn/v1/checkout/init",
            "sepay_sandbox_allowed_user_ids": [],
        }
    )
    async with auth_app.state.session_factory() as session:
        assert not (await session.get(User, uid)).is_platform_admin
    options = await auth_client.get(
        "/api/v1/billing/payments/sepay/options", headers=headers
    )
    assert options.json()["enabled"] is True
    live = await checkout(auth_client, headers)
    assert live.status_code == 201
    body = live.json()
    assert body["checkout_url"] == "https://pay.sepay.vn/v1/checkout/init"
    async with auth_app.state.session_factory() as session:
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        assert order.provider_environment == "production"
    event = paid(body)
    assert (await send(auth_client, event)).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "paid"
    async with auth_app.state.session_factory() as session:
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        sub = await session.get(Subscription, order.subscription_id)
        before = (sub.id, sub.period_start, sub.period_end)
    assert (await send(auth_client, event)).status_code == 200
    # Even a fixture authenticated with the current test key cannot activate
    # an old Sandbox order while the gateway operates in Production.
    assert (await send(auth_client, paid(sandbox_order))).status_code == 200
    async with auth_app.state.session_factory() as session:
        sub = await session.get(Subscription, before[0])
        assert (sub.id, sub.period_start, sub.period_end) == before
        old = await session.get(PaymentOrder, UUID(sandbox_order["payment_order_id"]))
        assert old.subscription_id is None
        assert old.failure_code == "PAYMENT_PROVIDER_ENVIRONMENT_MISMATCH"
    invoice = await auth_client.get(
        f"/api/v1/billing/invoices/{body['payment_order_id']}", headers=headers
    )
    assert invoice.json()["provider_environment"] == "production"
    assert invoice.json()["status"] == "paid"
