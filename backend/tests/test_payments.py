import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text, update

from alembic import command
from app.models.billing import BillingAuditEvent, Plan, Subscription
from app.models.payment import PaymentEvent, PaymentOrder
from app.models.user import User
from app.services.billing.subscriptions import SubscriptionService, add_months
from tests.business_helpers import authorization, register
from tests.test_auth import auth_app, auth_client
from tests.test_billing import activate, admin_setup

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration
BASE = "/api/v1/billing/payments"
IPN_KEY = "test-only-ipn-key"


@pytest.fixture(autouse=True)
def payment_config(monkeypatch):
    monkeypatch.setenv("SEPAY_ENABLED", "true")
    monkeypatch.setenv("SEPAY_ENV", "sandbox")
    monkeypatch.setenv("SEPAY_MERCHANT_ID", "TEST-MERCHANT")
    monkeypatch.setenv("SEPAY_SECRET_KEY", "test-only-signing-key")
    monkeypatch.setenv("SEPAY_IPN_SECRET_KEY", IPN_KEY)
    for field, path in (
        ("CHECKOUT", "checkout"),
        ("SUCCESS", "success"),
        ("ERROR", "error"),
        ("CANCEL", "cancel"),
    ):
        monkeypatch.setenv(
            f"SEPAY_{field}_URL", f"https://merchant.example.test/{path}"
        )


async def account(client, app):
    response = await register(client)
    uid = UUID(response.json()["user"]["id"])
    async with app.state.session_factory() as session, session.begin():
        (await session.get(User, uid)).email_verified_at = datetime.now(UTC)
    return authorization(response), uid


async def checkout(client, headers, code="desktop_starter", **changes):
    plan = next(
        p
        for p in (await client.get("/api/v1/billing/plans")).json()
        if p["code"] == code
    )
    return await client.post(
        f"{BASE}/sepay/checkout",
        headers=headers,
        json={"plan_id": plan["id"], "product_line": plan["device_scope"], **changes},
    )


def paid(body, **changes):
    fields = body["form"]
    payload = {
        "timestamp": 1757058220,
        "notification_type": "ORDER_PAID",
        "order": {
            "id": str(uuid4()),
            "order_status": "CAPTURED",
            "order_currency": "VND",
            "order_amount": fields["order_amount"] + ".00",
            "order_invoice_number": body["invoice_number"],
        },
        "transaction": {
            "id": str(uuid4()),
            "transaction_id": uuid4().hex,
            "transaction_type": "PAYMENT",
            "transaction_status": "APPROVED",
            "transaction_currency": "VND",
            "transaction_amount": fields["order_amount"],
            "payment_method": "CARD",
            "card_number": "DO-NOT-STORE-PAN",
            "cvv": "DO-NOT-STORE-CVV",
        },
        "customer": {"email": "DO-NOT-STORE-EMAIL"},
    }
    for section, values in changes.items():
        if isinstance(values, dict):
            payload[section].update(values)
        else:
            payload[section] = values
    return payload


async def send(client, payload, key=IPN_KEY):
    return await client.post(
        f"{BASE}/sepay/ipn", json=payload, headers={"X-Secret-Key": key} if key else {}
    )


async def status(client, headers, body):
    return (
        await client.get(f"{BASE}/{body['payment_order_id']}", headers=headers)
    ).json()


async def test_checkout_authority_snapshot_and_ownership(auth_client, auth_app):
    headers, uid = await account(auth_client, auth_app)
    assert (await checkout(auth_client, {})).status_code == 401
    unverified = authorization(await register(auth_client))
    assert (await checkout(auth_client, unverified)).status_code == 403
    assert (await checkout(auth_client, headers, "desktop_free")).status_code == 422
    assert (
        await checkout(auth_client, headers, product_line="mobile")
    ).status_code == 422
    assert (await checkout(auth_client, headers, amount=1)).status_code == 422
    assert (await checkout(auth_client, headers, user_id=str(uid))).status_code == 422
    assert (
        await checkout(auth_client, headers, plan_id=str(uuid4()))
    ).status_code == 404
    first = await checkout(auth_client, headers)
    second = await checkout(auth_client, headers)
    assert first.status_code == second.status_code == 201
    body = first.json()
    assert body["invoice_number"] != second.json()["invoice_number"]
    assert body["form"]["order_amount"] == "495330"
    assert body["form"]["currency"] == "VND"
    assert "payment_method" not in body["form"]
    assert body["payment_order_id"] in body["form"]["success_url"]
    assert "test-only-signing-key" not in first.text and IPN_KEY not in first.text
    other, _ = await account(auth_client, auth_app)
    assert (
        await auth_client.get(f"{BASE}/{body['payment_order_id']}", headers=other)
    ).status_code == 404
    async with auth_app.state.session_factory() as session, session.begin():
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        assert order.commercial_snapshot["max_projects"] == 5
        assert order.commercial_snapshot["billing_months"] == 1
        await session.execute(
            update(Plan)
            .where(Plan.id == order.plan_id)
            .values(max_projects=99, price_monthly_minor_units=600000)
        )
    assert (await send(auth_client, paid(body))).status_code == 200
    async with auth_app.state.session_factory() as session:
        sub = await session.scalar(
            select(Subscription).where(
                Subscription.user_id == uid,
                Subscription.status == "active",
                Subscription.device_scope == "desktop",
            )
        )
        assert (
            sub.snapshot["max_projects"] == 5
            and sub.snapshot["price_monthly_minor_units"] == 495330
        )
        assert sub.source == "sepay"
        event = await session.scalar(select(PaymentEvent))
        assert "DO-NOT-STORE" not in str(event.raw_payload)
    assert (await status(auth_client, headers, body))["status"] == "paid"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"order": {"order_amount": "1"}}, "PAYMENT_AMOUNT_MISMATCH"),
        (
            {"transaction": {"transaction_amount": "495330.01"}},
            "PAYMENT_AMOUNT_MISMATCH",
        ),
        ({"order": {"order_currency": "USD"}}, "PAYMENT_CURRENCY_MISMATCH"),
        ({"transaction": {"transaction_currency": "USD"}}, "PAYMENT_CURRENCY_MISMATCH"),
        ({"order": {"order_status": "FAILED"}}, "PAYMENT_PROVIDER_EVENT_INVALID"),
        (
            {"transaction": {"transaction_status": "DECLINED"}},
            "PAYMENT_PROVIDER_EVENT_INVALID",
        ),
        (
            {"transaction": {"transaction_type": "VOID"}},
            "PAYMENT_PROVIDER_EVENT_INVALID",
        ),
        ({"transaction": {"transaction_id": ""}}, "PAYMENT_PROVIDER_EVENT_INVALID"),
    ],
)
async def test_inconsistent_payment_review_without_activation(
    auth_client, auth_app, change, code
):
    headers, uid = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    assert (await send(auth_client, paid(body, **change))).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "review_required"
    async with auth_app.state.session_factory() as session:
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        assert order.failure_code == code and order.subscription_id is None
        sub = await session.scalar(
            select(Subscription).where(
                Subscription.user_id == uid, Subscription.status == "active"
            )
        )
        assert sub.snapshot["price_monthly_minor_units"] == 0


async def test_ipn_auth_unknown_invoice_unknown_event(auth_client, auth_app):
    headers, _ = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    payload = paid(body)
    for key in (None, "wrong"):
        assert (await send(auth_client, payload, key)).status_code == 401
    assert (await send(auth_client, {})).status_code == 422
    assert (
        await send(auth_client, paid(body, order={"order_invoice_number": "UNKNOWN"}))
    ).status_code == 200
    assert (
        await send(auth_client, paid(body, notification_type="OTHER"))
    ).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "checkout_created"
    async with auth_app.state.session_factory() as session:
        events = list(await session.scalars(select(PaymentEvent)))
        assert {e.processing_result for e in events} == {
            "PAYMENT_ORDER_NOT_FOUND",
            "ignored_notification",
        }


async def test_concurrent_duplicate_renewal_upgrade_downgrade(auth_client, auth_app):
    headers, uid = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    payload = paid(body)
    responses = await asyncio.gather(*(send(auth_client, payload) for _ in range(3)))
    assert all(r.status_code == 200 for r in responses)
    async with auth_app.state.session_factory() as session:
        sub = await session.get(
            Subscription,
            UUID((await status(auth_client, headers, body))["subscription_id"]),
        )
        initial_end = sub.period_end
    renewed = (await checkout(auth_client, headers)).json()
    renewal = paid(renewed)
    assert (await send(auth_client, renewal)).status_code == 200
    renewal["timestamp"] += 1
    assert (await send(auth_client, renewal)).status_code == 200
    renewal["transaction"]["payment_method"] = (
        "BANK_TRANSFER"  # different fingerprint, same transaction
    )
    assert (await send(auth_client, renewal)).status_code == 200
    async with auth_app.state.session_factory() as session:
        sub = await session.get(Subscription, sub.id)
        assert sub.period_end == add_months(initial_end, 1)
        assert (
            await session.scalar(
                select(func.count())
                .select_from(BillingAuditEvent)
                .where(
                    BillingAuditEvent.event_type
                    == "subscription_activated_from_payment"
                )
            )
            == 2
        )
    upgrade = (await checkout(auth_client, headers, "desktop_pro")).json()
    assert (await send(auth_client, paid(upgrade))).status_code == 200
    assert (await checkout(auth_client, headers)).status_code == 409
    summary = (await auth_client.get("/api/v1/billing/me", headers=headers)).json()
    assert summary["devices"][0]["plan"]["code"] == "desktop_pro"
    assert summary["devices"][1]["plan"]["code"] == "mobile_free"


async def test_provider_transaction_reuse_and_void(auth_client, auth_app):
    headers, _ = await account(auth_client, auth_app)
    first = (await checkout(auth_client, headers)).json()
    payload = paid(first)
    await send(auth_client, payload)
    other_headers, _ = await account(auth_client, auth_app)
    second = (await checkout(auth_client, other_headers)).json()
    replay = paid(second)
    replay["transaction"] = payload["transaction"]
    assert (await send(auth_client, replay)).status_code == 200
    assert (await status(auth_client, other_headers, second))[
        "status"
    ] == "review_required"
    before = await status(auth_client, headers, first)
    void = paid(first, notification_type="TRANSACTION_VOID")
    void["order"] = payload["order"]
    assert (await send(auth_client, void)).status_code == 200
    after = await status(auth_client, headers, first)
    assert (
        after["status"] == "review_required"
        and after["subscription_id"] == before["subscription_id"]
    )
    assert (await send(auth_client, payload)).status_code == 200
    assert (await status(auth_client, headers, first))["status"] == "review_required"


async def test_atomic_rollback_and_late_payment(auth_client, auth_app, monkeypatch):
    headers, _ = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    payload = paid(body)
    original = SubscriptionService.activate_from_payment
    monkeypatch.setattr(
        SubscriptionService,
        "activate_from_payment",
        AsyncMock(side_effect=RuntimeError("test activation failure")),
    )
    assert (await send(auth_client, payload)).status_code == 500
    async with auth_app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentEvent)) == 0
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        assert order.status == "checkout_created" and order.paid_at is None
    monkeypatch.setattr(SubscriptionService, "activate_from_payment", original)
    async with auth_app.state.session_factory() as session, session.begin():
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        order.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await status(auth_client, headers, body))["status"] == "expired"
    assert (await send(auth_client, payload)).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "review_required"


async def test_catalog_unsupported_and_expired_manual_compatibility(
    auth_client, auth_app
):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    async with auth_app.state.session_factory() as session, session.begin():
        (await session.get(User, uid)).email_verified_at = datetime.now(UTC)
        await session.execute(
            update(Plan).where(Plan.code == "mobile_starter").values(currency="USD")
        )
        await session.execute(
            update(Plan).where(Plan.code == "mobile_pro").values(active=False)
        )
    assert (await checkout(auth_client, headers, "mobile_starter")).status_code == 422
    async with auth_app.state.session_factory() as session:
        plan = await session.scalar(select(Plan).where(Plan.code == "mobile_pro"))
    assert (
        await checkout(auth_client, headers, plan_id=str(plan.id))
    ).status_code == 422
    assert (await activate(auth_client, admin, uid)).status_code == 201
    async with auth_app.state.session_factory() as session, session.begin():
        sub = await session.scalar(
            select(Subscription).where(
                Subscription.user_id == uid,
                Subscription.status == "active",
                Subscription.device_scope == "desktop",
            )
        )
        sub.period_start = datetime.now(UTC) - timedelta(days=60)
        sub.period_end = datetime.now(UTC) - timedelta(days=1)
    body = (await checkout(auth_client, headers)).json()
    assert (await send(auth_client, paid(body))).status_code == 200
    options = (await auth_client.get(f"{BASE}/sepay/options", headers=headers)).json()
    assert options["enabled"] and str(plan.id) not in options["eligible_plan_ids"]


async def test_migration_roundtrip_constraints(auth_app):
    async with auth_app.state.session_factory() as session, session.begin():
        connection = await session.connection()

        def roundtrip(sync):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync
            command.downgrade(config, "-1")
            command.upgrade(config, "head")

        await connection.run_sync(roundtrip)
        indexes = list(
            await session.scalars(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = 'payment_orders'"
                )
            )
        )
        assert {
            "uq_payment_orders_provider_transaction",
            "uq_payment_orders_provider_transaction_uuid",
            "ix_payment_orders_status",
        } <= set(indexes)


@pytest.mark.parametrize("field", ["id", "transaction_id", "order_id"])
async def test_provider_reference_conflict_across_users(auth_client, auth_app, field):
    first_headers, _ = await account(auth_client, auth_app)
    first = (await checkout(auth_client, first_headers)).json()
    first_payload = paid(first)
    await send(auth_client, first_payload)
    second_headers, _ = await account(auth_client, auth_app)
    second = (await checkout(auth_client, second_headers)).json()
    payload = paid(second)
    section, key = ("order", "id") if field == "order_id" else ("transaction", field)
    payload[section][key] = first_payload[section][key]
    assert (await send(auth_client, payload)).status_code == 200
    assert (await status(auth_client, second_headers, second))[
        "status"
    ] == "review_required"


async def test_corrupt_snapshot_review(auth_client, auth_app):
    headers, _ = await account(auth_client, auth_app)
    body = (await checkout(auth_client, headers)).json()
    async with auth_app.state.session_factory() as session, session.begin():
        order = await session.get(PaymentOrder, UUID(body["payment_order_id"]))
        order.commercial_snapshot = {
            **order.commercial_snapshot,
            "max_keywords": "invalid",
        }
    assert (await send(auth_client, paid(body))).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "review_required"


async def test_disabled_checkout(auth_client, auth_app):
    headers, _ = await account(auth_client, auth_app)
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"sepay_enabled": False}
    )
    assert (await checkout(auth_client, headers)).status_code == 503
    assert (await auth_client.get(f"{BASE}/sepay/options", headers=headers)).json() == {
        "enabled": False,
        "eligible_plan_ids": [],
    }


async def test_scheduled_transition_rechecked_at_confirmation(auth_client, auth_app):
    admin, headers, uid = await admin_setup(auth_client, auth_app)
    async with auth_app.state.session_factory() as session, session.begin():
        (await session.get(User, uid)).email_verified_at = datetime.now(UTC)
    body = (await checkout(auth_client, headers)).json()
    start = datetime.now(UTC) + timedelta(days=1)
    scheduled = await activate(
        auth_client,
        admin,
        uid,
        period_start=start.isoformat(),
        period_end=add_months(start, 1).isoformat(),
    )
    assert scheduled.status_code == 201
    assert (await checkout(auth_client, headers)).status_code == 409
    assert (await send(auth_client, paid(body))).status_code == 200
    assert (await status(auth_client, headers, body))["status"] == "review_required"


async def test_concurrent_transaction_reuse_across_orders(auth_client, auth_app):
    first_headers, _ = await account(auth_client, auth_app)
    second_headers, _ = await account(auth_client, auth_app)
    first = (await checkout(auth_client, first_headers)).json()
    second = (await checkout(auth_client, second_headers)).json()
    one, two = paid(first), paid(second)
    two["transaction"] = one["transaction"]
    responses = await asyncio.gather(send(auth_client, one), send(auth_client, two))
    assert all(response.status_code == 200 for response in responses)
    assert sorted(
        [
            (await status(auth_client, first_headers, first))["status"],
            (await status(auth_client, second_headers, second))["status"],
        ]
    ) == ["paid", "review_required"]


async def test_production_sandbox_restricts_checkout_to_admin_or_qa(
    auth_client, auth_app
):
    headers, uid = await account(auth_client, auth_app)
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"app_env": "production"}
    )
    assert (await checkout(auth_client, headers)).status_code == 503
    assert (await auth_client.get(f"{BASE}/sepay/options", headers=headers)).json()[
        "enabled"
    ] is False
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"sepay_sandbox_allowed_user_ids": [uid]}
    )
    assert (await checkout(auth_client, headers)).status_code == 201
    auth_app.state.settings = auth_app.state.settings.model_copy(
        update={"sepay_sandbox_allowed_user_ids": []}
    )
    async with auth_app.state.session_factory() as session, session.begin():
        (await session.get(User, uid)).is_platform_admin = True
    assert (await checkout(auth_client, headers)).status_code == 201
