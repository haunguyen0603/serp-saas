from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import delete, inspect, select

from app.core.security import hash_password
from app.db.models import Base
from app.models.keyword import Keyword
from app.models.project import Project
from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite
from app.models.user import User
from app.repositories.keyword import KeywordRepository
from app.repositories.project import ProjectRepository
from app.repositories.tracked_domain import TrackedDomainRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.repositories.user import UserRepository
from app.schemas.keyword import KeywordBulkCreate, KeywordCreate, KeywordUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.tracked_site import (
    TrackedDomainCreate,
    TrackedDomainUpdate,
    TrackedSiteCreate,
)
from app.services.keywords import KeywordService
from app.services.projects import ProjectService
from app.services.tracked_sites import TrackedSiteService
from tests.business_helpers import (
    PASSWORD,
    PROJECT,
    authorization,
    create_project,
    project_body,
    register,
)
from tests.test_auth import auth_app, auth_client

__all__ = ["auth_app", "auth_client"]
pytestmark = pytest.mark.integration


async def test_database_constraints_indexes_and_schema_match(auth_app: FastAPI) -> None:
    async with auth_app.state.session_factory() as session:
        connection = await session.connection()

        def check(sync_connection) -> None:
            inspector = inspect(sync_connection)
            assert {
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
            } <= set(inspector.get_table_names())
            indexes = {
                table: {
                    tuple(item["column_names"]) for item in inspector.get_indexes(table)
                }
                for table in (
                    "projects",
                    "keywords",
                    "tracked_sites",
                    "tracked_domains",
                    "rank_checks",
                    "rank_check_results",
                    "rankings",
                    "provider_usage",
                    "rank_check_provider_attempts",
                )
            }
            assert {
                ("user_id",),
                ("user_id", "status"),
                ("user_id", "created_at"),
            } <= indexes["projects"]
            assert {
                ("project_id",),
                ("project_id", "active"),
                ("project_id", "created_at"),
                ("project_id", "keyword_normalized"),
            } <= indexes["keywords"]
            assert {
                ("user_id",),
                ("user_id", "status"),
                ("user_id", "created_at"),
            } <= indexes["tracked_sites"]
            assert {
                ("user_id",),
                ("tracked_site_id",),
                ("tracked_site_id", "active"),
            } <= indexes["tracked_domains"]
            domain_indexes = {
                item["name"]: item for item in inspector.get_indexes("tracked_domains")
            }
            assert domain_indexes["uq_tracked_domains_one_primary"]["unique"] is True
            assert {
                ("keyword_id", "created_at"),
                ("project_id", "created_at"),
                ("user_id", "created_at"),
                ("status",),
            } <= indexes["rank_checks"]
            assert {("rank_check_id", "position")} <= indexes["rank_check_results"]
            assert {
                ("rank_check_id",),
                ("tracked_site_id", "created_at"),
            } <= indexes["rankings"]
            assert {("provider", "period_key")} <= indexes["provider_usage"]
            assert {
                ("rank_check_id", "attempt_number"),
                ("provider", "created_at"),
            } <= indexes["rank_check_provider_attempts"]
            assert (
                inspector.get_foreign_keys("projects")[0]["options"]["ondelete"]
                == "CASCADE"
            )
            assert (
                inspector.get_foreign_keys("keywords")[0]["options"]["ondelete"]
                == "CASCADE"
            )
            domain_fk = next(
                item
                for item in inspector.get_foreign_keys("tracked_domains")
                if item["referred_table"] == "tracked_sites"
            )
            assert domain_fk["constrained_columns"] == ["tracked_site_id", "user_id"]
            assert domain_fk["options"]["ondelete"] == "CASCADE"
            rank_check_fks = inspector.get_foreign_keys("rank_checks")
            assert {
                (tuple(item["constrained_columns"]), item["options"]["ondelete"])
                for item in rank_check_fks
            } == {
                (("project_id", "user_id"), "RESTRICT"),
                (("keyword_id", "project_id"), "RESTRICT"),
            }
            result_fk = inspector.get_foreign_keys("rank_check_results")[0]
            assert result_fk["options"]["ondelete"] == "RESTRICT"
            ranking_fks = {
                item["referred_table"]: item["options"]["ondelete"]
                for item in inspector.get_foreign_keys("rankings")
            }
            assert ranking_fks == {
                "rank_checks": "RESTRICT",
                "tracked_domains": "SET NULL",
                "tracked_sites": "SET NULL",
            }
            attempt_fk = inspector.get_foreign_keys("rank_check_provider_attempts")[0]
            assert attempt_fk["referred_table"] == "rank_checks"
            assert attempt_fk["options"]["ondelete"] == "CASCADE"
            assert (
                compare_metadata(
                    MigrationContext.configure(sync_connection), Base.metadata
                )
                == []
            )

        await connection.run_sync(check)


async def test_user_cascade_and_timezone_timestamps(
    auth_client: AsyncClient, auth_app: FastAPI
) -> None:
    registered = await register(auth_client)
    headers = authorization(registered)
    project = project_body(await create_project(auth_client, headers))
    site = (
        await auth_client.post(
            "/api/v1/tracked-sites",
            headers=headers,
            json={"name": "Site", "primary_domain": "site.example"},
        )
    ).json()
    for body in [project, site, site["domains"][0]]:
        assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
        assert datetime.fromisoformat(body["updated_at"]).tzinfo is not None
    async with auth_app.state.session_factory.begin() as session:
        await session.execute(
            delete(User).where(User.id == UUID(registered.json()["user"]["id"]))
        )
    async with auth_app.state.session_factory() as session:
        for model in (Project, Keyword, TrackedSite, TrackedDomain):
            assert (await session.scalars(select(model))).all() == []


async def test_repositories_and_services_without_http(auth_app: FastAPI) -> None:
    async with auth_app.state.session_factory.begin() as session:
        user = await UserRepository(session).create(
            "service@example.com", hash_password(PASSWORD), datetime.now(UTC)
        )
        projects = ProjectService(
            ProjectRepository(session), KeywordRepository(session)
        )
        result = await projects.create(user.id, ProjectCreate(**PROJECT))
        project = await projects.get(result.project.id, user.id)
        keywords = KeywordService(
            KeywordRepository(session), ProjectRepository(session)
        )
        first = await keywords.create(
            project.id, user.id, KeywordCreate(keyword="service keyword")
        )
        bulk = await keywords.bulk_create(
            project.id,
            user.id,
            KeywordBulkCreate(keywords=["service keyword", "new keyword"]),
        )
        assert bulk.created == 1 and bulk.skipped_duplicates == 1
        listed = await keywords.list(
            project.id, user.id, search="keyword", active="all", limit=50, cursor=None
        )
        assert len(listed.items) == 3
        assert (
            await keywords.update(
                first.id, project.id, user.id, KeywordUpdate(active=False)
            )
        ).active is False
        assert (
            await projects.update(
                project.id, user.id, ProjectUpdate(name="Service Project")
            )
        ).name == "Service Project"
        sites = TrackedSiteService(
            TrackedSiteRepository(session), TrackedDomainRepository(session)
        )
        site = await sites.create(
            user.id,
            TrackedSiteCreate(
                name="Service Site", primary_domain="old.example", aliases=[]
            ),
        )
        added = await sites.add_domain(
            site.id,
            user.id,
            TrackedDomainCreate(domain="new.example", make_primary=False),
        )
        promoted = await sites.update_domain(
            added.id, site.id, user.id, TrackedDomainUpdate(is_primary=True)
        )
        assert promoted.is_primary is True


async def test_openapi_documents_milestone_3_1_contract(
    auth_client: AsyncClient,
) -> None:
    schema = (await auth_client.get("/openapi.json")).json()
    paths = schema["paths"]
    assert {
        "/api/v1/projects",
        "/api/v1/projects/{project_id}",
        "/api/v1/projects/{project_id}/keywords",
        "/api/v1/projects/{project_id}/keywords/bulk",
        "/api/v1/projects/{project_id}/keywords/{keyword_id}",
        "/api/v1/tracked-sites",
        "/api/v1/tracked-sites/{site_id}",
        "/api/v1/tracked-sites/{site_id}/domains",
        "/api/v1/tracked-sites/{site_id}/domains/{domain_id}",
        "/api/v1/projects/{project_id}/rank-check-batches",
        "/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
        "/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}",
        "/api/v1/projects/{project_id}/rankings/latest",
    } <= set(paths)
    project = schema["components"]["schemas"]["ProjectResponse"]["properties"]
    keyword = schema["components"]["schemas"]["KeywordResponse"]["properties"]
    domain = schema["components"]["schemas"]["TrackedDomainResponse"]["properties"]
    assert not {"user_id", "domain", "default_device"} & set(project)
    assert not {
        "project_id",
        "user_id",
        "keyword_normalized",
        "device",
        "location",
    } & set(keyword)
    assert not {"user_id", "tracked_site_id"} & set(domain)
    for path, method in (
        ("/api/v1/projects/{project_id}/rank-check-batches", "post"),
        (
            "/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-check-batches",
            "post",
        ),
        (
            "/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks",
            "get",
        ),
        (
            "/api/v1/projects/{project_id}/keywords/{keyword_id}/rank-checks/{check_id}",
            "get",
        ),
        ("/api/v1/projects/{project_id}/rankings/latest", "get"),
    ):
        documented = set(paths[path][method]["responses"])
        assert {"200" if method == "get" else "202", "401", "404", "422"} <= documented


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
async def test_business_cors_preflight(auth_client: AsyncClient, method: str) -> None:
    response = await auth_client.options(
        "/api/v1/tracked-sites/00000000-0000-0000-0000-000000000000",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert method in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_bulk_logging_uses_counts_not_payload(
    auth_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    headers = authorization(await register(auth_client))
    project = project_body(await create_project(auth_client, headers))
    secret = "bulk phrase that must not be logged"
    with caplog.at_level("INFO"):
        response = await auth_client.post(
            f"/api/v1/projects/{project['id']}/keywords/bulk",
            headers=headers,
            json={"keywords": [secret]},
        )
    assert response.status_code == 201 and secret not in caplog.text
