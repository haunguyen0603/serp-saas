import asyncio

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from app.db.models import Base
from tests.test_migrations import isolated_migration_context


@pytest.mark.integration
def test_alert_migration_roundtrip_and_metadata(settings, monkeypatch):
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")

    async def verify():
        async with engine.connect() as connection:
            from alembic.migration import MigrationContext

            diff = await connection.run_sync(
                lambda sync: compare_metadata(
                    MigrationContext.configure(sync), Base.metadata
                )
            )
            assert diff == []
            indexes = await connection.run_sync(
                lambda sync: inspect(sync).get_indexes("ranking_alerts")
            )
            assert {i["name"] for i in indexes} >= {
                "ix_ranking_alerts_inbox",
                "ix_ranking_alerts_unread",
                "ix_ranking_alerts_project",
            }

    try:
        command.upgrade(config, "head")
        asyncio.run(verify())
        command.downgrade(config, "0016_sepay_payments")
        command.upgrade(config, "head")
        asyncio.run(verify())
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())
