"""Operator-only bootstrap: python -m scripts.platform_admin EMAIL [--revoke]."""

import argparse
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.user import User


async def main(email: str, revoke: bool) -> None:
    engine = create_engine(get_settings())
    try:
        async with create_session_factory(engine)() as session, session.begin():
            user = await session.scalar(
                select(User).where(User.email == email.strip().lower())
            )
            if user is None:
                raise SystemExit("Account not found. Register the account first.")
            user.is_platform_admin = not revoke
        print("Platform administrator access updated.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--revoke", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.email, args.revoke))
