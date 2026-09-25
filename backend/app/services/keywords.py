import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.models.keyword import Keyword
from app.repositories.keyword import (
    KeywordRepository,
    KeywordUpdateValues,
    KeywordValues,
)
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rank_check import RankCheckRepository
from app.schemas.keyword import (
    KeywordActiveFilter,
    KeywordBulkCreate,
    KeywordBulkResult,
    KeywordCreate,
    KeywordListResponse,
    KeywordResponse,
    KeywordUpdate,
)
from app.services.billing.entitlements import EntitlementService
from app.services.normalization import decode_cursor, encode_cursor, normalize_keyword

logger = logging.getLogger(__name__)


def prepare_keyword_values(
    raw_keywords: list[str],
) -> tuple[list[KeywordValues], int]:
    unique: dict[str, KeywordValues] = {}
    skipped_empty = 0
    for raw in raw_keywords:
        try:
            display, normalized = normalize_keyword(raw)
        except AppError as error:
            if error.code == "INVALID_KEYWORD" and not raw.strip():
                skipped_empty += 1
                continue
            raise
        unique.setdefault(
            normalized,
            KeywordValues(keyword=display, keyword_normalized=normalized),
        )
    return list(unique.values()), skipped_empty


class KeywordService:
    def __init__(
        self,
        keywords: KeywordRepository,
        projects: ProjectRepository,
        rank_checks: RankCheckRepository | None = None,
        organizations: KeywordOrganizationRepository | None = None,
    ) -> None:
        self.keywords = keywords
        self.projects = projects
        self.rank_checks = rank_checks
        self.organizations = organizations

    async def _require_project(self, project_id: UUID, user_id: UUID) -> None:
        if await self.projects.get_for_user(project_id, user_id) is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")

    async def create(
        self, project_id: UUID, user_id: UUID, data: KeywordCreate
    ) -> Keyword:
        await self._require_project(project_id, user_id)
        if self.organizations is None and (data.group_id or data.tag_ids):
            raise AppError(
                503, "ORGANIZATION_UNAVAILABLE", "Organization is unavailable."
            )
        if (
            data.group_id is not None
            and self.organizations is not None
            and len(
                await self.organizations.groups_for_project(project_id, {data.group_id})
            )
            != 1
        ):
            raise AppError(
                422, "INVALID_GROUP_ASSIGNMENT", "Group must belong to this Project."
            )
        selected_tags = set(data.tag_ids)
        if self.organizations is not None and len(
            await self.organizations.tags_for_project(project_id, selected_tags)
        ) != len(selected_tags):
            raise AppError(
                422, "INVALID_TAG_ASSIGNMENT", "Tags must belong to this Project."
            )
        display, normalized = normalize_keyword(data.keyword)
        await EntitlementService(self.keywords.session).keyword_add(
            user_id, project_id, [normalized]
        )
        try:
            async with self.keywords.session.begin_nested():
                keyword = await self.keywords.create_for_project(
                    project_id,
                    KeywordValues(keyword=display, keyword_normalized=normalized),
                )
                if keyword is not None:
                    keyword.keyword_group_id = data.group_id
                    if self.organizations is not None:
                        await self.organizations.replace_keyword_tags(
                            project_id, keyword.id, selected_tags
                        )
                    await self.keywords.session.flush()
        except IntegrityError:
            raise AppError(
                422,
                "CROSS_PROJECT_ASSIGNMENT",
                "Organization references must belong to this Project.",
            ) from None
        if keyword is None:
            raise AppError(409, "KEYWORD_ALREADY_EXISTS", "Keyword already exists.")
        refreshed = await self.keywords.get_for_user_project(
            keyword.id, project_id, user_id
        )
        assert refreshed is not None
        logger.info("Keyword created", extra={"keyword_id": str(keyword.id)})
        return refreshed

    async def bulk_create(
        self, project_id: UUID, user_id: UUID, data: KeywordBulkCreate
    ) -> KeywordBulkResult:
        await self._require_project(project_id, user_id)
        values, skipped_empty = prepare_keyword_values(data.keywords)
        await EntitlementService(self.keywords.session).keyword_add(
            user_id, project_id, [v["keyword_normalized"] for v in values]
        )
        created = await self.keywords.bulk_create_for_project(project_id, values)
        skipped_duplicates = len(data.keywords) - skipped_empty - len(created)
        logger.info(
            "Keywords bulk created",
            extra={
                "project_id": str(project_id),
                "submitted": len(data.keywords),
                "created_count": len(created),
            },
        )
        return KeywordBulkResult(
            submitted=len(data.keywords),
            normalized_unique=len(values),
            created=len(created),
            skipped_duplicates=skipped_duplicates,
            skipped_empty=skipped_empty,
            items=[KeywordResponse.from_keyword(item) for item in created],
        )

    async def get(self, keyword_id: UUID, project_id: UUID, user_id: UUID) -> Keyword:
        keyword = await self.keywords.get_for_user_project(
            keyword_id, project_id, user_id
        )
        if keyword is None:
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
        return keyword

    async def list(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        search: str | None,
        active: KeywordActiveFilter,
        limit: int,
        cursor: str | None,
        group_id: str | None = None,
        tag_ids: str | None = None,
        tag_match: str = "any",
    ) -> KeywordListResponse:
        await self._require_project(project_id, user_id)
        selected_active = None if active == "all" else active == "true"
        group_filter: UUID | str | None = None
        if group_id == "none":
            group_filter = "none"
        elif group_id:
            try:
                selected_group = UUID(group_id)
            except ValueError:
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                ) from None
            if (
                self.organizations is None
                or len(
                    await self.organizations.groups_for_project(
                        project_id, {selected_group}
                    )
                )
                != 1
            ):
                raise AppError(
                    422, "INVALID_GROUP_ASSIGNMENT", "Group filter is invalid."
                )
            group_filter = selected_group
        if tag_match not in {"any", "all"}:
            raise AppError(422, "INVALID_TAG_MATCH", "Tag match mode is invalid.")
        selected_tags: set[UUID] = set()
        if tag_ids:
            try:
                selected_tags = {UUID(value) for value in tag_ids.split(",") if value}
            except ValueError:
                raise AppError(
                    422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid."
                ) from None
            if not selected_tags or len(selected_tags) > 100:
                raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
            if self.organizations is None or len(
                await self.organizations.tags_for_project(project_id, selected_tags)
            ) != len(selected_tags):
                raise AppError(422, "INVALID_TAG_ASSIGNMENT", "Tag filter is invalid.")
        items, has_more = await self.keywords.list_for_user_project(
            project_id,
            user_id,
            search=search.strip() if search and search.strip() else None,
            active=selected_active,
            group_filter=group_filter,  # type: ignore[arg-type]
            tag_ids=selected_tags,
            tag_match=tag_match,  # type: ignore[arg-type]
            limit=limit,
            cursor=decode_cursor(cursor),
        )
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id)
            if has_more and items
            else None
        )
        return KeywordListResponse(
            items=[KeywordResponse.from_keyword(item) for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def update(
        self,
        keyword_id: UUID,
        project_id: UUID,
        user_id: UUID,
        data: KeywordUpdate,
    ) -> Keyword:
        entitlements = EntitlementService(self.keywords.session)
        await entitlements.subscriptions.repo.lock(user_id)
        current = await self.get(keyword_id, project_id, user_id)
        if data.active is True and not current.active:
            project = await self.projects.get_for_user(project_id, user_id)
            if project and project.status == "active":
                await entitlements.expansion(user_id, project.device, keywords=1)
        organization_changed = bool(
            {"group_id", "tag_ids"}.intersection(data.model_fields_set)
        )
        if organization_changed and self.organizations is None:
            raise AppError(
                503, "ORGANIZATION_UNAVAILABLE", "Organization is unavailable."
            )
        if (
            data.group_id is not None
            and self.organizations is not None
            and len(
                await self.organizations.groups_for_project(project_id, {data.group_id})
            )
            != 1
        ):
            raise AppError(
                422, "INVALID_GROUP_ASSIGNMENT", "Group must belong to this Project."
            )
        selected_tags = set(data.tag_ids or [])
        tags_valid = (
            await self.organizations.tags_for_project(project_id, selected_tags)
            if "tag_ids" in data.model_fields_set and self.organizations is not None
            else []
        )
        if "tag_ids" in data.model_fields_set and len(tags_valid) != len(selected_tags):
            raise AppError(
                422, "INVALID_TAG_ASSIGNMENT", "Tags must belong to this Project."
            )
        values = KeywordUpdateValues()
        if "keyword" in data.model_fields_set and data.keyword is not None:
            display, normalized = normalize_keyword(data.keyword)
            values["keyword"] = display
            values["keyword_normalized"] = normalized
        if "active" in data.model_fields_set and data.active is not None:
            values["active"] = data.active
        try:
            async with self.keywords.session.begin_nested():
                keyword = await self.keywords.update_for_user_project(
                    keyword_id, project_id, user_id, values
                )
                if keyword is not None and "group_id" in data.model_fields_set:
                    keyword.keyword_group_id = data.group_id
                if (
                    keyword is not None
                    and "tag_ids" in data.model_fields_set
                    and self.organizations is not None
                ):
                    await self.organizations.replace_keyword_tags(
                        project_id, keyword.id, selected_tags
                    )
                await self.keywords.session.flush()
        except IntegrityError:
            if organization_changed:
                raise AppError(
                    422,
                    "CROSS_PROJECT_ASSIGNMENT",
                    "Organization references must belong to this Project.",
                ) from None
            raise AppError(
                409, "KEYWORD_ALREADY_EXISTS", "Keyword already exists."
            ) from None
        if keyword is None:
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
        refreshed = await self.keywords.get_for_user_project(
            keyword.id, project_id, user_id
        )
        assert refreshed is not None
        logger.info("Keyword updated", extra={"keyword_id": str(keyword.id)})
        return refreshed

    async def delete(self, keyword_id: UUID, project_id: UUID, user_id: UUID) -> None:
        if self.rank_checks and await self.rank_checks.has_for_keyword(
            keyword_id, project_id, user_id
        ):
            raise AppError(
                409,
                "HISTORY_EXISTS",
                "Pause this Keyword because ranking history exists.",
            )
        if not await self.keywords.delete_for_user_project(
            keyword_id, project_id, user_id
        ):
            raise AppError(404, "KEYWORD_NOT_FOUND", "Keyword not found.")
        logger.info("Keyword deleted", extra={"keyword_id": str(keyword_id)})
