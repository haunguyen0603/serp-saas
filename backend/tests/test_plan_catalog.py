import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.billing import PlanChange, Subscription, UsagePeriod
from tests.business_helpers import authorization, register
from tests.test_auth import auth_app, auth_client
from tests.test_billing import activate, admin_setup

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def catalog(client, admin):
    response = await client.get("/api/v1/admin/plans", headers=admin)
    assert response.status_code == 200
    return {plan["code"]: plan for plan in response.json()}


def edit(plan, **changes):
    return {
        "expected_updated_at": plan["updated_at"],
        **{
            key: plan[key]
            for key in (
                "price_monthly_minor_units",
                "max_projects",
                "max_keywords",
                "monthly_keyword_checks",
            )
        },
        **changes,
    }


async def test_plan_catalog_admin_only_and_validation(auth_client, auth_app):
    admin, user, _ = await admin_setup(auth_client, auth_app)
    original = await catalog(auth_client, admin)
    data = edit(original["desktop_starter"])
    for headers, expected in [({}, 401), (user, 403)]:
        for path in ["/admin/plans", "/admin/plans/history"]:
            assert (
                await auth_client.get("/api/v1" + path, headers=headers)
            ).status_code == expected
        assert (
            await auth_client.patch(
                "/api/v1/admin/plans/desktop_starter", headers=headers, json=data
            )
        ).status_code == expected
    for changes in [
        {"max_projects": -1},
        {"max_keywords": 1.5},
        {"monthly_keyword_checks": 2147483648},
        {"max_projects": True},
        {"max_keywords": "20"},
        {"device_scope": "mobile"},
        {"scheduled_checks_enabled": False},
        {"price_monthly_minor_units": 0},
        {"price_monthly_minor_units": -1},
    ]:
        result = await auth_client.patch(
            "/api/v1/admin/plans/desktop_starter",
            headers=admin,
            json={**data, **changes},
        )
        assert result.status_code == 422
    assert (
        await auth_client.patch(
            "/api/v1/admin/plans/desktop_free",
            headers=admin,
            json=edit(original["desktop_free"], price_monthly_minor_units=100),
        )
    ).status_code == 422
    assert (
        await auth_client.patch("/api/v1/admin/plans/missing", headers=admin, json=data)
    ).status_code == 404
    assert await catalog(auth_client, admin) == original
    assert (
        await auth_client.get("/api/v1/admin/plans/history", headers=admin)
    ).json() == []


@pytest.mark.parametrize("device", ["desktop", "mobile"])
async def test_plan_edit_preserves_existing_terms_and_updates_new_activations(
    auth_client, auth_app, device
):
    admin, user, uid = await admin_setup(auth_client, auth_app)
    code = f"{device}_starter"
    first = (await activate(auth_client, admin, uid, code)).json()
    other = "mobile" if device == "desktop" else "desktop"
    original = await catalog(auth_client, admin)
    before_billing = (await auth_client.get("/api/v1/billing/me", headers=user)).json()
    async with auth_app.state.session_factory() as session:
        periods_before = [
            (
                p.id,
                p.keyword_check_limit,
                p.committed_keyword_checks,
                p.reserved_keyword_checks,
            )
            for p in await session.scalars(select(UsagePeriod))
        ]
    updates = dict(
        price_monthly_minor_units=2950,
        max_projects=7,
        max_keywords=777,
        monthly_keyword_checks=7777,
    )
    result = await auth_client.patch(
        f"/api/v1/admin/plans/{code}",
        headers=admin,
        json=edit(original[code], **updates),
    )
    assert result.status_code == 200
    for key, value in updates.items():
        assert result.json()[key] == value
    public = {
        p["code"]: p for p in (await auth_client.get("/api/v1/billing/plans")).json()
    }
    assert len(public) == 6 and public[code]["price_monthly_minor_units"] == 2950
    assert (
        public[f"{other}_starter"]["max_keywords"]
        == original[f"{other}_starter"]["max_keywords"]
    )
    after_billing = (await auth_client.get("/api/v1/billing/me", headers=user)).json()
    assert before_billing == after_billing
    async with auth_app.state.session_factory() as session:
        assert (await session.get(Subscription, UUID(first["id"]))).snapshot == first[
            "snapshot"
        ]
        assert [
            (
                p.id,
                p.keyword_check_limit,
                p.committed_keyword_checks,
                p.reserved_keyword_checks,
            )
            for p in await session.scalars(select(UsagePeriod))
        ] == periods_before
        changes = list(await session.scalars(select(PlanChange)))
        assert len(changes) == 1
        assert changes[0].before["max_keywords"] == original[code]["max_keywords"]
        assert changes[0].after["max_keywords"] == 777
        assert changes[0].actor_user_id is not None
    extension = await auth_client.post(
        f"/api/v1/admin/customers/{uid}/subscriptions/{first['id']}/extend",
        headers=admin,
        json={"period_end": (datetime.now(UTC) + timedelta(days=120)).isoformat()},
    )
    assert (
        extension.status_code == 200
        and extension.json()["snapshot"] == first["snapshot"]
    )
    new_uid = (await register(auth_client, "new-customer")).json()["user"]["id"]
    created = await activate(auth_client, admin, new_uid, code)
    assert created.status_code == 201
    for key, value in updates.items():
        assert created.json()["snapshot"][key] == value
    history = (
        await auth_client.get("/api/v1/admin/plans/history", headers=admin)
    ).json()
    assert len(history) == 1 and history[0]["after"]["code"] == code


async def test_plan_edit_race_rejects_stale_save(auth_client, auth_app):
    admin, _, _ = await admin_setup(auth_client, auth_app)
    plan = (await catalog(auth_client, admin))["desktop_free"]
    results = await asyncio.gather(
        *(
            auth_client.patch(
                "/api/v1/admin/plans/desktop_free",
                headers=admin,
                json=edit(plan, max_projects=value),
            )
            for value in [3, 5]
        )
    )
    assert sorted(result.status_code for result in results) == [200, 409]
    assert (
        next(result for result in results if result.status_code == 409).json()["error"][
            "code"
        ]
        == "PLAN_CHANGED"
    )
    account = await register(auth_client, "new-free")
    billing = (
        await auth_client.get("/api/v1/billing/me", headers=authorization(account))
    ).json()
    assert (
        billing["devices"][0]["plan"]["max_projects"]
        == next(result for result in results if result.status_code == 200).json()[
            "max_projects"
        ]
    )
