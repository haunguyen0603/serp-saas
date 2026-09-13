"""Local fake-provider fixture for browser regressions requiring Pro schedules."""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.user import User
from app.services.billing.subscriptions import SubscriptionService


async def main(email: str) -> None:
    settings = get_settings()
    if (
        settings.app_env not in ("development", "test")
        or settings.serp_enabled_providers != "fake"
        or settings.task_queue_provider != "local"
    ):
        raise SystemExit(
            "Verification fixtures require local/fake development services."
        )
    engine = create_engine(settings)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            user = await session.scalar(select(User).where(User.email == email))
            if user is None:
                raise SystemExit("Fixture account not found.")
            await SubscriptionService(session).activate(
                user.id,
                user.id,
                "desktop_pro",
                datetime.now(UTC),
                datetime.now(UTC) + timedelta(days=30),
                "manual_bank_transfer",
                "verification-fixture",
                "Local fake-provider verification only",
                True,
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    asyncio.run(main(parser.parse_args().email))
