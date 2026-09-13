import pytest
from httpx import AsyncClient

from tests.business_helpers import authorization, create_project, register
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def test_overview_requires_authentication(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/api/v1/overview")).status_code == 401


async def test_overview_matches_billing_and_isolates_customers(
    auth_client: AsyncClient,
) -> None:
    owner = authorization(await register(auth_client))
    other = authorization(await register(auth_client))
    assert (await create_project(auth_client, owner)).status_code == 201
    own = (await auth_client.get("/api/v1/overview", headers=owner)).json()
    empty = (await auth_client.get("/api/v1/overview", headers=other)).json()
    billing = (await auth_client.get("/api/v1/billing/me", headers=owner)).json()
    assert own["billing"] == billing
    assert sum(d["projects_used"] for d in own["billing"]["devices"]) == 1
    assert sum(d["projects_used"] for d in empty["billing"]["devices"]) == 0
    assert own["recent_batches"] == empty["recent_batches"] == []
    assert own["active_tracked_sites"] == 0
