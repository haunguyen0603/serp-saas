"""Deterministic billing/admin smoke; local DB + fake provider only."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.user import User


async def promote(email: str) -> None:
    engine = create_engine(get_settings())
    try:
        async with create_session_factory(engine)() as session, session.begin():
            user = await session.scalar(select(User).where(User.email == email))
            assert user
            user.is_platform_admin = True
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    assert settings.task_queue_provider == "local"
    assert settings.serp_enabled_providers == "fake"
    with httpx.Client(
        base_url=f"http://127.0.0.1:{settings.backend_port}", timeout=30
    ) as client:

        def register(label):
            email = f"m6a-{label}-{uuid4().hex}@example.com"
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "m6a deterministic password",
                    "accept_terms": True,
                },
            )
            assert response.status_code == 201
            return (
                email,
                UUID(response.json()["user"]["id"]),
                {"Authorization": f"Bearer {response.json()['access_token']}"},
            )

        email, _, admin = register("admin")
        asyncio.run(promote(email))
        _, uid, user = register("customer")
        root = f"/api/v1/admin/customers/{uid}"
        assert client.get(root + "/billing", headers=user).status_code == 403
        free = client.get("/api/v1/billing/me", headers=user).json()
        assert [d["plan"]["code"] for d in free["devices"]] == [
            "desktop_free",
            "mobile_free",
        ]
        body = {
            "plan_code": "desktop_starter",
            "period_start": datetime.now(UTC).isoformat(),
            "period_end": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
            "payment_method": "manual_bank_transfer",
            "payment_reference": "M6A-BANK-001",
            "note": "private smoke note",
        }
        desktop = client.post(root + "/subscriptions", headers=admin, json=body)
        assert desktop.status_code == 201
        mobile = client.post(
            root + "/subscriptions",
            headers=admin,
            json={**body, "plan_code": "mobile_starter"},
        )
        assert mobile.status_code == 201
        assert (
            client.post(
                root + f"/subscriptions/{desktop.json()['id']}/extend",
                headers=admin,
                json={
                    "period_end": (datetime.now(UTC) + timedelta(days=120)).isoformat()
                },
            ).status_code
            == 200
        )
        adjustment = client.post(
            root + "/usage-adjustments",
            headers=admin,
            json={"device_scope": "desktop", "amount": 500, "note": "goodwill"},
        )
        assert adjustment.json()["devices"][0]["usage"]["remaining"] == 5500
        assert adjustment.json()["devices"][1]["usage"]["remaining"] == 1000
        history = client.get(root + "/subscriptions", headers=admin)
        assert "M6A-BANK-001" in history.text
        assert (
            "private smoke note"
            not in client.get("/api/v1/billing/me", headers=user).text
        )
        print(
            "PASS: customer Free fallback, admin authorization, "
            "independent paid activation, extension, audit/history and adjustment; "
            "zero external operations"
        )


if __name__ == "__main__":
    main()
