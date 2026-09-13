from uuid import uuid4

from httpx import AsyncClient, Response

PASSWORD = "milestone three test password"
PROJECT = {
    "name": "Main Website",
    "search_engine": "google",
    "country_code": "vn",
    "language_code": "vi",
    "device": "desktop",
    "location": " Ho  Chi Minh City ",
    "keywords": ["initial keyword"],
}


async def register(client: AsyncClient, label: str = "business") -> Response:
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{label}-{uuid4().hex}@example.com",
            "password": PASSWORD,
            "accept_terms": True,
        },
    )


def authorization(response: Response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_project(
    client: AsyncClient, headers: dict[str, str], **changes: object
) -> Response:
    return await client.post(
        "/api/v1/projects", headers=headers, json={**PROJECT, **changes}
    )


def project_body(response: Response) -> dict[str, object]:
    return response.json()["project"]


async def grant_plan(app, account, code="desktop_pro"):
    """Commercial setup for regressions that require paid resource/schedule limits."""
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.services.billing.subscriptions import SubscriptionService

    user_id = UUID(account.json()["user"]["id"])
    async with app.state.session_factory() as session, session.begin():
        await SubscriptionService(session).activate(
            user_id,
            user_id,
            code,
            datetime.now(UTC),
            datetime.now(UTC) + timedelta(days=90),
            "manual_bank_transfer",
            "test-fixture",
            None,
            True,
        )
