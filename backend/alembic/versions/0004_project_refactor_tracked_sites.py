"""Refactor Projects and create the user-global tracked-domain registry.

This semantic migration is intentionally irreversible. After users edit the new
Tracked Site registry, a downgrade cannot reconstruct which domain used to be on
which Project or safely merge deterministically split Projects.
"""

import re
import unicodedata
from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid5

import sqlalchemy as sa

from alembic import op

revision: str = "0004_project_refactor_sites"
down_revision: str | None = "0003_projects_keywords"
branch_labels: str | None = None
depends_on: str | None = None

_whitespace = re.compile(r"\s+")


def _normalized_location(value: str | None) -> str:
    if value is None:
        return ""
    return _whitespace.sub(" ", unicodedata.normalize("NFC", value)).strip().casefold()


def _normalized_domain(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(f"Cannot migrate malformed Project domain: {value!r}")
    hostname = parsed.hostname
    if hostname is None:
        raise RuntimeError(f"Cannot migrate malformed Project domain: {value!r}")
    try:
        return hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise RuntimeError(
            f"Cannot migrate malformed Project domain: {value!r}"
        ) from error


def _derived_name(
    name: str, key: tuple[str, str, str, str, str], location: str | None
) -> str:
    _, country, language, device, _ = key
    suffix = f" — {country}/{language}/{device}"
    if location:
        suffix += f"/{location}"
    if len(suffix) >= 200:
        return suffix[:200].rstrip()
    return f"{name[: 200 - len(suffix)]}{suffix}".strip()


def _create_registry_tables() -> None:
    op.create_table(
        "tracked_sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="tracked_site_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 200",
            name="ck_tracked_sites_name_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_tracked_sites_id_user_id"),
    )
    op.create_index("ix_tracked_sites_user_id", "tracked_sites", ["user_id"])
    op.create_index(
        "ix_tracked_sites_user_id_status", "tracked_sites", ["user_id", "status"]
    )
    op.create_index(
        "ix_tracked_sites_user_id_created_at",
        "tracked_sites",
        ["user_id", "created_at"],
    )
    op.create_table(
        "tracked_domains",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_site_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(domain) BETWEEN 1 AND 253",
            name="ck_tracked_domains_domain_length",
        ),
        sa.CheckConstraint(
            "NOT is_primary OR active",
            name="ck_tracked_domains_primary_domain_must_be_active",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_site_id", "user_id"],
            ["tracked_sites.id", "tracked_sites.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "domain", name="uq_tracked_domains_user_domain"),
    )
    op.create_index("ix_tracked_domains_user_id", "tracked_domains", ["user_id"])
    op.create_index(
        "ix_tracked_domains_tracked_site_id", "tracked_domains", ["tracked_site_id"]
    )
    op.create_index(
        "ix_tracked_domains_tracked_site_id_active",
        "tracked_domains",
        ["tracked_site_id", "active"],
    )
    op.create_index(
        "uq_tracked_domains_one_primary",
        "tracked_domains",
        ["tracked_site_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def _backfill_tracked_sites(projects: list[dict[str, Any]]) -> None:
    bind = op.get_bind()
    domains: dict[tuple[UUID, str], dict[str, Any]] = {}
    for project in projects:
        domain = _normalized_domain(project["domain"])
        key = (project["user_id"], domain)
        current = domains.get(key)
        if current is None or (project["created_at"], project["id"]) < (
            current["created_at"],
            current["id"],
        ):
            domains[key] = project
    for (user_id, domain), project in sorted(
        domains.items(), key=lambda item: (str(item[0][0]), item[0][1])
    ):
        site_id = uuid5(user_id, f"tracked-site:{domain}")
        domain_id = uuid5(user_id, f"tracked-domain:{domain}")
        bind.execute(
            sa.text(
                """
                INSERT INTO tracked_sites
                    (id, user_id, name, status, created_at, updated_at)
                VALUES (:id, :user_id, :name, 'active', :created_at, :updated_at)
                """
            ),
            {
                "id": site_id,
                "user_id": user_id,
                "name": domain,
                "created_at": project["created_at"],
                "updated_at": project["updated_at"],
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO tracked_domains
                    (id, user_id, tracked_site_id, domain, is_primary, active,
                     created_at, updated_at)
                VALUES
                    (:id, :user_id, :site_id, :domain, true, true,
                     :created_at, :updated_at)
                """
            ),
            {
                "id": domain_id,
                "user_id": user_id,
                "site_id": site_id,
                "domain": domain,
                "created_at": project["created_at"],
                "updated_at": project["updated_at"],
            },
        )


def _split_projects(projects: list[dict[str, Any]]) -> None:
    bind = op.get_bind()
    keyword_rows = list(
        bind.execute(
            sa.text(
                """
                SELECT id, project_id, keyword, keyword_normalized,
                       search_engine, country_code, language_code, device,
                       location, location_normalized, active, created_at, updated_at
                FROM keywords
                ORDER BY project_id, id
                """
            )
        ).mappings()
    )
    by_project: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    for row in keyword_rows:
        by_project[row["project_id"]].append(dict(row))

    for project in sorted(projects, key=lambda item: str(item["id"])):
        rows = by_project.get(project["id"], [])
        if not rows:
            continue
        groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = (
            defaultdict(list)
        )
        for row in rows:
            key = (
                row["search_engine"],
                row["country_code"],
                row["language_code"],
                row["device"],
                row["location_normalized"],
            )
            groups[key].append(row)
        default_key = (
            project["default_search_engine"],
            project["default_country_code"],
            project["default_language_code"],
            project["default_device"],
            _normalized_location(project["default_location"]),
        )
        original_key = (
            default_key
            if default_key in groups
            else sorted(groups, key=lambda key: (-len(groups[key]), key))[0]
        )
        ordered_keys = [
            original_key,
            *sorted(key for key in groups if key != original_key),
        ]
        for index, key in enumerate(ordered_keys):
            representative = groups[key][0]
            if index == 0:
                target_id = project["id"]
                bind.execute(
                    sa.text(
                        """
                        UPDATE projects
                        SET default_search_engine = :search_engine,
                            default_country_code = :country_code,
                            default_language_code = :language_code,
                            default_device = :device,
                            default_location = :location
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": target_id,
                        "search_engine": key[0],
                        "country_code": key[1],
                        "language_code": key[2],
                        "device": key[3],
                        "location": representative["location"],
                    },
                )
            else:
                signature = "|".join(key)
                target_id = uuid5(project["id"], f"serp-environment:{signature}")
                name = _derived_name(project["name"], key, representative["location"])
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO projects
                            (id, user_id, name, domain, default_search_engine,
                             default_country_code, default_language_code,
                             default_device, default_location, status,
                             created_at, updated_at)
                        VALUES
                            (:id, :user_id, :name, :domain, :search_engine,
                             :country_code, :language_code, :device, :location,
                             :status, :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": target_id,
                        "user_id": project["user_id"],
                        "name": name,
                        "domain": project["domain"],
                        "search_engine": key[0],
                        "country_code": key[1],
                        "language_code": key[2],
                        "device": key[3],
                        "location": representative["location"],
                        "status": project["status"],
                        "created_at": project["created_at"],
                        "updated_at": project["updated_at"],
                    },
                )
                bind.execute(
                    sa.text(
                        "UPDATE keywords SET project_id = :target WHERE id = ANY(:ids)"
                    ),
                    {
                        "target": target_id,
                        "ids": [row["id"] for row in groups[key]],
                    },
                )


def upgrade() -> None:
    _create_registry_tables()
    bind = op.get_bind()
    projects = [
        dict(row)
        for row in bind.execute(
            sa.text(
                """
                SELECT id, user_id, name, domain, default_search_engine,
                       default_country_code, default_language_code,
                       default_device, default_location, status,
                       created_at, updated_at
                FROM projects
                ORDER BY user_id, id
                """
            )
        ).mappings()
    ]
    _backfill_tracked_sites(projects)
    _split_projects(projects)

    op.drop_constraint("uq_keywords_tracking_configuration", "keywords", type_="unique")
    for constraint in (
        "ck_keywords_search_engine",
        "ck_keywords_country_code_format",
        "ck_keywords_language_code_format",
        "ck_keywords_device_value",
    ):
        op.drop_constraint(constraint, "keywords", type_="check")
    for column in (
        "search_engine",
        "country_code",
        "language_code",
        "device",
        "location",
        "location_normalized",
    ):
        op.drop_column("keywords", column)
    op.create_unique_constraint(
        "uq_keywords_project_keyword_normalized",
        "keywords",
        ["project_id", "keyword_normalized"],
    )

    op.drop_constraint("ck_projects_domain_length", "projects", type_="check")
    op.drop_column("projects", "domain")
    op.alter_column(
        "projects", "default_search_engine", new_column_name="search_engine"
    )
    op.alter_column("projects", "default_country_code", new_column_name="country_code")
    op.alter_column(
        "projects", "default_language_code", new_column_name="language_code"
    )
    op.alter_column("projects", "default_device", new_column_name="device")
    op.alter_column("projects", "default_location", new_column_name="location")


def downgrade() -> None:
    raise RuntimeError(
        "Revision 0004 is intentionally irreversible: the original Project/domain "
        "and per-Keyword configuration relationships cannot be reconstructed safely."
    )
