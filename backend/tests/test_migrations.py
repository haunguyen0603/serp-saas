import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import Settings


def isolated_migration_context(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    schema = f"migration_test_{uuid4().hex}"
    url = settings.database_url.get_secret_value()
    admin = create_async_engine(url, poolclass=NullPool)

    async def admin_sql(sql: str) -> None:
        async with admin.begin() as connection:
            await connection.execute(text(sql))

    asyncio.run(admin_sql(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": schema}},
    )
    import sqlalchemy.ext.asyncio as async_sqlalchemy

    original_create = async_sqlalchemy.create_async_engine

    def isolated_engine(database_url: str, **kwargs: Any) -> AsyncEngine:
        kwargs["connect_args"] = {"server_settings": {"search_path": schema}}
        return original_create(database_url, **kwargs)

    monkeypatch.setattr(async_sqlalchemy, "create_async_engine", isolated_engine)
    return schema, admin, engine, admin_sql


@pytest.mark.integration
def test_fresh_database_upgrade_and_forward_only_boundary(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")

    async def revision() -> str | None:
        async with engine.connect() as connection:
            return await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )

    try:
        command.upgrade(config, "head")
        assert asyncio.run(revision()) == "0011_reports"

        async def tables() -> set[str]:
            async with engine.connect() as connection:
                return await connection.run_sync(
                    lambda sync: set(inspect(sync).get_table_names())
                )

        assert asyncio.run(tables()) == {
            "alembic_version",
            "plans",
            "plan_changes",
            "subscriptions",
            "usage_periods",
            "usage_reservations",
            "usage_events",
            "billing_audit_events",
            "users",
            "refresh_tokens",
            "projects",
            "keywords",
            "tracked_sites",
            "tracked_domains",
            "rank_checks",
            "rank_check_results",
            "rankings",
            "provider_usage",
            "rank_check_provider_attempts",
            "rank_check_batches",
            "rank_check_jobs",
            "project_rank_schedules",
            "keyword_groups",
            "keyword_tags",
            "keyword_tag_assignments",
            "generated_reports",
            "report_schedules",
            "report_delivery_attempts",
        }
        command.downgrade(config, "0005_rank_tracking")
        assert asyncio.run(revision()) == "0005_rank_tracking"
        command.upgrade(config, "head")
        assert asyncio.run(revision()) == "0011_reports"
        with pytest.raises(RuntimeError, match="intentionally irreversible"):
            command.downgrade(config, "0003_projects_keywords")
        assert asyncio.run(revision()) == "0011_reports"
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())


@pytest.mark.integration
def test_realistic_milestone_3_data_is_preserved_and_split(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")
    user_a, user_b = uuid4(), uuid4()
    project_default, project_duplicate, project_other_user = uuid4(), uuid4(), uuid4()
    keyword_ids = [uuid4() for _ in range(4)]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with engine.begin() as connection:
            for user_id, email in [
                (user_a, "a@example.com"),
                (user_b, "b@example.com"),
            ]:
                await connection.execute(
                    text(
                        "INSERT INTO users "
                        "(id,email,password_hash,status,terms_accepted_at,"
                        "created_at,updated_at) VALUES "
                        "(:id,:email,'hash','active',:now,:now,:now)"
                    ),
                    {"id": user_id, "email": email, "now": now},
                )
            projects = [
                (
                    project_default,
                    user_a,
                    "Main",
                    "Example.COM",
                    "VN",
                    "vi",
                    "desktop",
                    "Ho Chi Minh City",
                ),
                (
                    project_duplicate,
                    user_a,
                    "Duplicate domain",
                    "example.com",
                    "US",
                    "en",
                    "desktop",
                    None,
                ),
                (
                    project_other_user,
                    user_b,
                    "Other user",
                    "example.com",
                    "US",
                    "en",
                    "desktop",
                    None,
                ),
            ]
            for (
                project_id,
                user_id,
                name,
                domain,
                country,
                language,
                device,
                location,
            ) in projects:
                await connection.execute(
                    text(
                        "INSERT INTO projects "
                        "(id,user_id,name,domain,default_search_engine,"
                        "default_country_code,default_language_code,"
                        "default_device,default_location,status,created_at,"
                        "updated_at) VALUES (:id,:user_id,:name,:domain,"
                        "'google',:country,:language,:device,:location,"
                        "'active',:now,:now)"
                    ),
                    {
                        "id": project_id,
                        "user_id": user_id,
                        "name": name,
                        "domain": domain,
                        "country": country,
                        "language": language,
                        "device": device,
                        "location": location,
                        "now": now,
                    },
                )
            rows = [
                (
                    keyword_ids[0],
                    project_default,
                    "same query",
                    "same query",
                    "VN",
                    "vi",
                    "desktop",
                    "Ho Chi Minh City",
                    "ho chi minh city",
                    True,
                ),
                (
                    keyword_ids[1],
                    project_default,
                    "Same Query",
                    "same query",
                    "TH",
                    "en",
                    "mobile",
                    "Bangkok",
                    "bangkok",
                    True,
                ),
                (
                    keyword_ids[2],
                    project_default,
                    "third query",
                    "third query",
                    "TH",
                    "en",
                    "mobile",
                    "Bangkok",
                    "bangkok",
                    False,
                ),
                (
                    keyword_ids[3],
                    project_other_user,
                    "other user query",
                    "other user query",
                    "US",
                    "en",
                    "desktop",
                    None,
                    "",
                    True,
                ),
            ]
            for (
                keyword_id,
                project_id,
                keyword,
                normalized,
                country,
                language,
                device,
                location,
                location_normalized,
                active,
            ) in rows:
                await connection.execute(
                    text(
                        "INSERT INTO keywords "
                        "(id,project_id,keyword,keyword_normalized,search_engine,"
                        "country_code,language_code,device,location,"
                        "location_normalized,active,created_at,updated_at) "
                        "VALUES (:id,:project_id,:keyword,:normalized,'google',"
                        ":country,:language,:device,:location,"
                        ":location_normalized,:active,:now,:now)"
                    ),
                    {
                        "id": keyword_id,
                        "project_id": project_id,
                        "keyword": keyword,
                        "normalized": normalized,
                        "country": country,
                        "language": language,
                        "device": device,
                        "location": location,
                        "location_normalized": location_normalized,
                        "active": active,
                        "now": now,
                    },
                )

    async def verify() -> None:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT count(*) FROM keywords")) == 4
            assert await connection.scalar(text("SELECT count(*) FROM projects")) == 4
            assert (
                await connection.scalar(text("SELECT count(*) FROM tracked_sites")) == 2
            )
            assert (
                await connection.scalar(text("SELECT count(*) FROM tracked_domains"))
                == 2
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM tracked_domains "
                        "WHERE domain='example.com'"
                    )
                )
                == 2
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM tracked_domains "
                        "WHERE user_id=:user_id AND domain='example.com'"
                    ),
                    {"user_id": user_a},
                )
                == 1
            )
            original = (
                (
                    await connection.execute(
                        text(
                            "SELECT search_engine,country_code,language_code,"
                            "device,location FROM projects WHERE id=:id"
                        ),
                        {"id": project_default},
                    )
                )
                .mappings()
                .one()
            )
            assert dict(original) == {
                "search_engine": "google",
                "country_code": "VN",
                "language_code": "vi",
                "device": "desktop",
                "location": "Ho Chi Minh City",
            }
            split = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,name,country_code,language_code,device,"
                            "location,status FROM projects WHERE user_id=:user_id "
                            "AND id NOT IN (:one,:two)"
                        ),
                        {
                            "user_id": user_a,
                            "one": project_default,
                            "two": project_duplicate,
                        },
                    )
                )
                .mappings()
                .one()
            )
            assert (
                split["country_code"],
                split["language_code"],
                split["device"],
                split["location"],
                split["status"],
            ) == ("TH", "en", "mobile", "Bangkok", "active")
            assert "TH/en/mobile/Bangkok" in split["name"]
            moved = (
                await connection.execute(
                    text(
                        "SELECT keyword,active FROM keywords "
                        "WHERE project_id=:id ORDER BY keyword"
                    ),
                    {"id": split["id"]},
                )
            ).all()
            assert moved == [("Same Query", True), ("third query", False)]
            columns = {
                item["name"]
                for item in await connection.run_sync(
                    lambda sync: inspect(sync).get_columns("keywords")
                )
            }
            assert (
                not {
                    "search_engine",
                    "country_code",
                    "language_code",
                    "device",
                    "location",
                    "location_normalized",
                }
                & columns
            )
            project_columns = {
                item["name"]
                for item in await connection.run_sync(
                    lambda sync: inspect(sync).get_columns("projects")
                )
            }
            assert (
                "domain" not in project_columns and "search_engine" in project_columns
            )

    try:
        command.upgrade(config, "0003_projects_keywords")
        asyncio.run(seed())
        command.upgrade(config, "0004_project_refactor_sites")
        asyncio.run(verify())
        command.upgrade(config, "head")
        asyncio.run(verify())

        async def verify_rank_tables() -> None:
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(text("SELECT count(*) FROM rank_checks"))
                    == 0
                )
                assert (
                    await connection.scalar(
                        text("SELECT count(*) FROM rank_check_results")
                    )
                    == 0
                )
                assert (
                    await connection.scalar(text("SELECT count(*) FROM rankings")) == 0
                )

        asyncio.run(verify_rank_tables())
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())


@pytest.mark.integration
def test_existing_milestone_4_history_survives_upgrade_and_round_trip(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")
    (
        user_id,
        project_id,
        keyword_id,
        check_id,
        result_id,
        site_id,
        domain_id,
        ranking_id,
    ) = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    now = datetime.now(UTC)

    async def seed_and_verify() -> None:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users "
                    "(id,email,password_hash,status,terms_accepted_at,"
                    "created_at,updated_at) "
                    "VALUES (:id,'m4@example.com','hash','active',:now,:now,:now)"
                ),
                {"id": user_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id,user_id,name,search_engine,country_code,language_code,device,"
                    "location,status,created_at,updated_at) VALUES "
                    "(:id,:user_id,'M4 Project','google','VN','vi','desktop',"
                    "'Ho Chi Minh City','active',:now,:now)"
                ),
                {"id": project_id, "user_id": user_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO keywords "
                    "(id,project_id,keyword,keyword_normalized,active,"
                    "created_at,updated_at) "
                    "VALUES (:id,:project_id,'legacy query','legacy query',"
                    "true,:now,:now)"
                ),
                {"id": keyword_id, "project_id": project_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO tracked_sites "
                    "(id,user_id,name,status,created_at,updated_at) VALUES "
                    "(:id,:user_id,'Legacy Site','active',:now,:now)"
                ),
                {"id": site_id, "user_id": user_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO tracked_domains "
                    "(id,user_id,tracked_site_id,domain,is_primary,active,"
                    "created_at,updated_at) VALUES "
                    "(:id,:user_id,:site_id,'example.com',true,true,:now,:now)"
                ),
                {
                    "id": domain_id,
                    "user_id": user_id,
                    "site_id": site_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO rank_checks "
                    "(id,user_id,project_id,keyword_id,provider,status,query_snapshot,"
                    "search_engine_snapshot,country_code_snapshot,language_code_snapshot,"
                    "device_snapshot,location_snapshot,result_limit,provider_request_count,"
                    "provider_request_id,provider_metadata,requested_at,completed_at,"
                    "created_at) VALUES "
                    "(:id,:user_id,:project_id,:keyword_id,'serpapi',"
                    "'succeeded','legacy query','google','VN','vi','desktop',"
                    "'Ho Chi Minh City',10,1,'legacy-request','{\"legacy\": true}',"
                    ":now,:now,:now)"
                ),
                {
                    "id": check_id,
                    "user_id": user_id,
                    "project_id": project_id,
                    "keyword_id": keyword_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO rank_check_results "
                    "(id,rank_check_id,position,title,url,hostname,created_at) "
                    "VALUES (:id,:check_id,1,'Legacy','https://example.com',"
                    "'example.com',:now)"
                ),
                {"id": result_id, "check_id": check_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO rankings "
                    "(id,rank_check_id,tracked_site_id,tracked_domain_id,"
                    "tracked_site_name_snapshot,matched_domain_snapshot,position,"
                    "result_url,result_hostname,title,created_at) VALUES "
                    "(:id,:check_id,:site_id,:domain_id,'Legacy Site','example.com',"
                    "1,'https://example.com','example.com','Legacy',:now)"
                ),
                {
                    "id": ranking_id,
                    "check_id": check_id,
                    "site_id": site_id,
                    "domain_id": domain_id,
                    "now": now,
                },
            )

    async def verify() -> None:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT provider,provider_request_count,query_snapshot,"
                        "country_code_snapshot FROM rank_checks WHERE id=:id"
                    ),
                    {"id": check_id},
                )
            ).one()
            assert row == ("serpapi", 1, "legacy query", "VN")
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM rank_check_results WHERE id=:id"),
                    {"id": result_id},
                )
                == 1
            )
            ranking = (
                await connection.execute(
                    text(
                        "SELECT tracked_site_name_snapshot,matched_domain_snapshot,"
                        "position FROM rankings WHERE id=:id"
                    ),
                    {"id": ranking_id},
                )
            ).one()
            assert ranking == ("Legacy Site", "example.com", 1)

    try:
        command.upgrade(config, "0005_rank_tracking")
        asyncio.run(seed_and_verify())
        command.upgrade(config, "head")
        asyncio.run(verify())

        async def verify_new_tables() -> None:
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(
                        text("SELECT count(*) FROM rank_check_provider_attempts")
                    )
                    == 0
                )
                assert (
                    await connection.scalar(text("SELECT count(*) FROM provider_usage"))
                    == 0
                )

        asyncio.run(verify_new_tables())

        async def seed_m41_accounting() -> None:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO provider_usage "
                        "(id,provider,period_type,period_key,request_count,"
                        "success_count,failure_count,fallback_count) "
                        "VALUES (:id,'serpapi','monthly','2026-09',1,1,0,0)"
                    ),
                    {"id": uuid4()},
                )
                await connection.execute(
                    text(
                        "INSERT INTO rank_check_provider_attempts "
                        "(id,rank_check_id,provider,attempt_number,status,"
                        "started_at,completed_at,provider_request_count) "
                        "VALUES (:id,:check,'serpapi',1,'succeeded',:now,:now,1)"
                    ),
                    {"id": uuid4(), "check": check_id, "now": now},
                )

        async def verify_m41_accounting() -> None:
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(
                        text("SELECT request_count FROM provider_usage")
                    )
                    == 1
                )
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM rank_check_provider_attempts "
                            "WHERE rank_check_id=:id"
                        ),
                        {"id": check_id},
                    )
                    == 1
                )

        # Seed the previous head, then verify actual M4.1 accounting survives M5.
        command.downgrade(config, "0006_multi_provider_routing")
        asyncio.run(seed_m41_accounting())
        command.upgrade(config, "head")
        asyncio.run(verify())
        asyncio.run(verify_m41_accounting())
        command.downgrade(config, "0006_multi_provider_routing")
        asyncio.run(verify_m41_accounting())
        command.upgrade(config, "head")
        asyncio.run(verify_m41_accounting())
        command.downgrade(config, "0005_rank_tracking")
        asyncio.run(verify())
        command.upgrade(config, "head")
        asyncio.run(verify())
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())


@pytest.mark.integration
def test_m5_round_trip_and_schema_drift(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "0006_multi_provider_routing")
        command.upgrade(config, "head")
        command.check(config)
        command.downgrade(config, "0006_multi_provider_routing")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())


@pytest.mark.integration
def test_m6a_existing_users_schedules_and_pending_jobs(settings, monkeypatch):
    schema, admin, engine, admin_sql = isolated_migration_context(settings, monkeypatch)
    config = Config("alembic.ini")
    user, project, keyword, batch, job, schedule = [uuid4() for _ in range(6)]

    async def seed():
        async with engine.begin() as connection:
            for sql, params in [
                (
                    "INSERT INTO users (id,email,password_hash,terms_accepted_at) VALUES (:id,'legacy@example.com','hash',now())",  # noqa: E501
                    {"id": user},
                ),
                (
                    "INSERT INTO projects (id,user_id,name,country_code,language_code,device) VALUES (:id,:user,'Legacy','VN','vi','desktop')",  # noqa: E501
                    {"id": project, "user": user},
                ),
                (
                    "INSERT INTO keywords (id,project_id,keyword,keyword_normalized) VALUES (:id,:project,'old','old')",  # noqa: E501
                    {"id": keyword, "project": project},
                ),
                (
                    "INSERT INTO project_rank_schedules (id,user_id,project_id,enabled,frequency,timezone,local_time,weekday,next_run_at) VALUES (:id,:user,:project,true,'daily','UTC','07:00',0,now())",  # noqa: E501
                    {"id": schedule, "user": user, "project": project},
                ),
                (
                    "INSERT INTO rank_check_batches (id,user_id,project_id,trigger_type,status,requested_keyword_count) VALUES (:id,:user,:project,'manual_project','pending',1)",  # noqa: E501
                    {"id": batch, "user": user, "project": project},
                ),
                (
                    "INSERT INTO rank_check_jobs (id,user_id,project_id,keyword_id,batch_id,status,attempt_count,max_attempts) VALUES (:id,:user,:project,:keyword,:batch,'pending',0,5)",  # noqa: E501
                    {
                        "id": job,
                        "user": user,
                        "project": project,
                        "keyword": keyword,
                        "batch": batch,
                    },
                ),
            ]:
                await connection.execute(text(sql), params)

    async def verify():
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM subscriptions WHERE status='active'")
                )
                == 2
            )
            assert await connection.scalar(text("SELECT count(*) FROM plans")) == 6
            assert not await connection.scalar(
                text("SELECT enabled FROM project_rank_schedules")
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM billing_audit_events WHERE event_type='schedule_disabled_due_to_plan'"  # noqa: E501
                    )
                )
                == 1
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM usage_reservations WHERE status='reserved'"  # noqa: E501
                    )
                )
                == 1
            )
            assert (
                await connection.scalar(
                    text("SELECT sum(reserved_keyword_checks) FROM usage_periods")
                )
                == 1
            )
            assert (
                await connection.scalar(text("SELECT status FROM rank_check_jobs"))
                == "pending"
            )
            assert (
                await connection.scalar(text("SELECT keyword FROM keywords")) == "old"
            )
            assert not await connection.scalar(
                text("SELECT is_platform_admin FROM users")
            )

    try:
        command.upgrade(config, "0007_async_rank_check_jobs")
        asyncio.run(seed())
        command.upgrade(config, "head")
        asyncio.run(verify())
        command.check(config)
        command.downgrade(config, "0007_async_rank_check_jobs")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        asyncio.run(engine.dispose())
        asyncio.run(admin_sql(f'DROP SCHEMA "{schema}" CASCADE'))
        asyncio.run(admin.dispose())
