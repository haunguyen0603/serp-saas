import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.models.keyword_organization import KeywordGroup, KeywordTag
from app.models.project import Project
from app.repositories.keyword_organization import KeywordOrganizationRepository
from app.repositories.project import ProjectRepository
from app.schemas.keyword_organization import (
    KeywordBulkOrganization,
    KeywordBulkOrganizationResult,
    KeywordGroupListResponse,
    KeywordGroupResponse,
    KeywordTagListResponse,
    KeywordTagResponse,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.services.billing.entitlements import EntitlementService
from app.services.normalization import normalize_organization_name

logger = logging.getLogger(__name__)


class KeywordOrganizationService:
    def __init__(
        self,
        organizations: KeywordOrganizationRepository,
        projects: ProjectRepository,
    ) -> None:
        self.organizations = organizations
        self.projects = projects

    async def _project(self, project_id: UUID, user_id: UUID) -> Project:
        project = await self.projects.get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        return project

    @staticmethod
    def _group_response(
        group: KeywordGroup, active_keyword_count: int
    ) -> KeywordGroupResponse:
        return KeywordGroupResponse(
            id=group.id,
            name=group.name,
            active_keyword_count=active_keyword_count,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    @staticmethod
    def _tag_response(tag: KeywordTag, active_keyword_count: int) -> KeywordTagResponse:
        return KeywordTagResponse(
            id=tag.id,
            name=tag.name,
            active_keyword_count=active_keyword_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )

    async def list_groups(
        self, project_id: UUID, user_id: UUID
    ) -> KeywordGroupListResponse:
        await self._project(project_id, user_id)
        rows = await self.organizations.list_groups(project_id, user_id)
        return KeywordGroupListResponse(
            items=[
                self._group_response(row.entity, row.active_keyword_count)  # type: ignore[arg-type]
                for row in rows
            ]
        )

    async def list_tags(
        self, project_id: UUID, user_id: UUID
    ) -> KeywordTagListResponse:
        await self._project(project_id, user_id)
        rows = await self.organizations.list_tags(project_id, user_id)
        return KeywordTagListResponse(
            items=[
                self._tag_response(row.entity, row.active_keyword_count)  # type: ignore[arg-type]
                for row in rows
            ]
        )

    async def create_group(
        self, project_id: UUID, user_id: UUID, data: OrganizationCreate
    ) -> KeywordGroupResponse:
        await self._project(project_id, user_id)
        name, normalized = normalize_organization_name(
            data.name, maximum=80, code="INVALID_GROUP_NAME"
        )
        try:
            async with self.organizations.session.begin_nested():
                entity = await self.organizations.create_group(
                    project_id, name, normalized
                )
        except IntegrityError:
            raise AppError(
                409, "DUPLICATE_GROUP_NAME", "A Group with this name already exists."
            ) from None
        return self._group_response(entity, 0)

    async def create_tag(
        self, project_id: UUID, user_id: UUID, data: OrganizationCreate
    ) -> KeywordTagResponse:
        await self._project(project_id, user_id)
        name, normalized = normalize_organization_name(
            data.name, maximum=40, code="INVALID_TAG_NAME"
        )
        try:
            async with self.organizations.session.begin_nested():
                entity = await self.organizations.create_tag(
                    project_id, name, normalized
                )
        except IntegrityError:
            raise AppError(
                409, "DUPLICATE_TAG_NAME", "A Tag with this name already exists."
            ) from None
        return self._tag_response(entity, 0)

    async def update_group(
        self,
        project_id: UUID,
        group_id: UUID,
        user_id: UUID,
        data: OrganizationUpdate,
    ) -> KeywordGroupResponse:
        group = await self.organizations.get_group(project_id, user_id, group_id)
        if group is None:
            raise AppError(404, "KEYWORD_GROUP_NOT_FOUND", "Keyword Group not found.")
        name, normalized = normalize_organization_name(
            data.name, maximum=80, code="INVALID_GROUP_NAME"
        )
        try:
            async with self.organizations.session.begin_nested():
                group.name = name
                group.normalized_name = normalized
                await self.organizations.session.flush()
                await self.organizations.session.refresh(group)
        except IntegrityError:
            raise AppError(
                409, "DUPLICATE_GROUP_NAME", "A Group with this name already exists."
            ) from None
        count = next(
            row.active_keyword_count
            for row in await self.organizations.list_groups(project_id, user_id)
            if row.entity.id == group.id
        )
        return self._group_response(group, count)

    async def update_tag(
        self,
        project_id: UUID,
        tag_id: UUID,
        user_id: UUID,
        data: OrganizationUpdate,
    ) -> KeywordTagResponse:
        tag = await self.organizations.get_tag(project_id, user_id, tag_id)
        if tag is None:
            raise AppError(404, "KEYWORD_TAG_NOT_FOUND", "Keyword Tag not found.")
        name, normalized = normalize_organization_name(
            data.name, maximum=40, code="INVALID_TAG_NAME"
        )
        try:
            async with self.organizations.session.begin_nested():
                tag.name = name
                tag.normalized_name = normalized
                await self.organizations.session.flush()
                await self.organizations.session.refresh(tag)
        except IntegrityError:
            raise AppError(
                409, "DUPLICATE_TAG_NAME", "A Tag with this name already exists."
            ) from None
        count = next(
            row.active_keyword_count
            for row in await self.organizations.list_tags(project_id, user_id)
            if row.entity.id == tag.id
        )
        return self._tag_response(tag, count)

    async def delete_group(
        self, project_id: UUID, group_id: UUID, user_id: UUID
    ) -> None:
        group = await self.organizations.get_group(project_id, user_id, group_id)
        if group is None:
            raise AppError(404, "KEYWORD_GROUP_NOT_FOUND", "Keyword Group not found.")
        await self.organizations.delete_group(group)

    async def delete_tag(self, project_id: UUID, tag_id: UUID, user_id: UUID) -> None:
        tag = await self.organizations.get_tag(project_id, user_id, tag_id)
        if tag is None:
            raise AppError(404, "KEYWORD_TAG_NOT_FOUND", "Keyword Tag not found.")
        await self.organizations.delete_tag(tag)

    async def bulk_organize(
        self,
        project_id: UUID,
        user_id: UUID,
        data: KeywordBulkOrganization,
    ) -> KeywordBulkOrganizationResult:
        project = await self._project(project_id, user_id)
        keyword_ids = set(data.keyword_ids)
        tag_ids = set(data.tag_ids or [])
        if data.operation == "restore":
            await EntitlementService(
                self.organizations.session
            ).subscriptions.repo.lock(user_id)
        keywords = await self.organizations.keywords_for_update(project_id, keyword_ids)
        if len(keywords) != len(keyword_ids):
            raise AppError(
                404,
                "KEYWORD_NOT_FOUND",
                "One or more selected Keywords were not found.",
            )
        if (
            data.group_id is not None
            and len(
                await self.organizations.groups_for_project(project_id, {data.group_id})
            )
            != 1
        ):
            raise AppError(
                422, "INVALID_GROUP_ASSIGNMENT", "Group must belong to this Project."
            )
        if tag_ids and len(
            await self.organizations.tags_for_project(project_id, tag_ids)
        ) != len(tag_ids):
            raise AppError(
                422, "INVALID_TAG_ASSIGNMENT", "Tags must belong to this Project."
            )
        assignment_count: int | None = None
        try:
            async with self.organizations.session.begin_nested():
                if data.operation == "assign_group":
                    changed = await self.organizations.bulk_assign_group(
                        project_id, keyword_ids, data.group_id
                    )
                elif data.operation == "add_tags":
                    changed, assignment_count = await self.organizations.bulk_add_tags(
                        project_id, keyword_ids, tag_ids
                    )
                elif data.operation == "remove_tags":
                    (
                        changed,
                        assignment_count,
                    ) = await self.organizations.bulk_remove_tags(
                        project_id, keyword_ids, tag_ids
                    )
                elif data.operation == "replace_tags":
                    (
                        changed,
                        assignment_count,
                    ) = await self.organizations.bulk_replace_tags(
                        project_id, keyword_ids, tag_ids
                    )
                else:
                    target = data.operation == "restore"
                    if target and project.status == "active":
                        restoring = sum(not keyword.active for keyword in keywords)
                        await EntitlementService(self.organizations.session).expansion(
                            user_id, project.device, keywords=restoring
                        )
                    changed = await self.organizations.bulk_set_active(
                        project_id, keyword_ids, target
                    )
        except IntegrityError:
            raise AppError(
                422,
                "CROSS_PROJECT_ASSIGNMENT",
                "Organization references must belong to this Project.",
            ) from None
        logger.info(
            "Keyword bulk organization updated",
            extra={
                "project_id": str(project_id),
                "operation": data.operation,
                "selected_count": len(keyword_ids),
                "affected_keyword_count": len(changed),
            },
        )
        return KeywordBulkOrganizationResult(
            operation=data.operation,
            selected_count=len(keyword_ids),
            affected_keyword_count=len(changed),
            assignment_count=assignment_count,
        )
