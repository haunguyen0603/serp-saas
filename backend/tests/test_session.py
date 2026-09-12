from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from app.core.config import Settings
from app.db.session import create_engine, get_db


@pytest.mark.parametrize("fail", [False, True])
async def test_session_transaction_and_cleanup(fail: bool) -> None:
    transaction = AsyncMock()
    session = AsyncMock()
    session.begin = MagicMock(return_value=transaction)
    context = AsyncMock()
    context.__aenter__.return_value = session
    factory = MagicMock(return_value=context)
    request = Request(
        {
            "type": "http",
            "app": SimpleNamespace(state=SimpleNamespace(session_factory=factory)),
        }
    )
    dependency = get_db(request)
    assert await anext(dependency) is session
    if fail:
        with pytest.raises(RuntimeError, match="rollback"):
            await dependency.athrow(RuntimeError("rollback"))
        assert transaction.__aexit__.call_args.args[0] is RuntimeError
    else:
        with pytest.raises(StopAsyncIteration):
            await anext(dependency)
        assert transaction.__aexit__.call_args.args == (None, None, None)
    context.__aexit__.assert_awaited_once()


@pytest.mark.integration
async def test_real_commit_and_rollback(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                await connection.execute(
                    text("CREATE TEMP TABLE session_probe (value int)")
                )
            factory = async_sessionmaker(connection, expire_on_commit=False)
            request = Request(
                {
                    "type": "http",
                    "app": SimpleNamespace(
                        state=SimpleNamespace(session_factory=factory)
                    ),
                }
            )
            success = get_db(request)
            session = await anext(success)
            await session.execute(text("INSERT INTO session_probe VALUES (1)"))
            with pytest.raises(StopAsyncIteration):
                await anext(success)

            failure = get_db(request)
            session = await anext(failure)
            await session.execute(text("INSERT INTO session_probe VALUES (2)"))
            with pytest.raises(RuntimeError):
                await failure.athrow(RuntimeError("rollback"))

            assert (
                await connection.scalar(text("SELECT sum(value) FROM session_probe"))
                == 1
            )
    finally:
        await engine.dispose()
