import logging
from uuid import UUID

from app.core.errors import AppError
from app.models.project import Project, ProjectStatus
from app.repositories.keyword import KeywordRepository
from app.repositories.project import ProjectRepository, ProjectUpdateValues
from app.repositories.rank_check import RankCheckRepository
from app.schemas.project import (
    InitialKeywordResult,
    ProjectCreate,
    ProjectCreateResult,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusFilter,
    ProjectUpdate,
)
from app.services.billing.entitlements import EntitlementService
from app.services.keywords import prepare_keyword_values
from app.services.normalization import (
    decode_cursor,
    encode_cursor,
    normalize_country_code,
    normalize_device,
    normalize_language_code,
    normalize_location,
    normalize_name,
    normalize_search_engine,
)

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        keywords: KeywordRepository,
        rank_checks: RankCheckRepository | None = None,
    ) -> None:
        self.projects = projects
        self.keywords = keywords
        self.rank_checks = rank_checks

    async def create(self, user_id: UUID, data: ProjectCreate) -> ProjectCreateResult:
        values, skipped_empty = prepare_keyword_values(data.keywords)
        if not values:
            raise AppError(
                422,
                "PROJECT_REQUIRES_KEYWORDS",
                "A Project requires at least one valid keyword.",
            )
        await EntitlementService(self.projects.session).expansion(
            user_id, normalize_device(data.device), projects=1, keywords=len(values)
        )
        project = await self.projects.create_for_user(
            user_id,
            name=normalize_name(data.name),
            search_engine=normalize_search_engine(data.search_engine),
            country_code=normalize_country_code(data.country_code),
            language_code=normalize_language_code(data.language_code),
            device=normalize_device(data.device),
            location=normalize_location(data.location),
        )
        created = await self.keywords.bulk_create_for_project(project.id, values)
        if len(created) != len(values):
            raise RuntimeError("Initial Project keywords were not fully persisted")
        skipped_duplicates = len(data.keywords) - skipped_empty - len(created)
        logger.info(
            "Project created",
            extra={
                "project_id": str(project.id),
                "submitted": len(data.keywords),
                "created_count": len(created),
            },
        )
        return ProjectCreateResult(
            project=ProjectResponse.from_project(project, len(created)),
            keywords=InitialKeywordResult(
                submitted=len(data.keywords),
                normalized_unique=len(values),
                created=len(created),
                skipped_duplicates=skipped_duplicates,
                skipped_empty=skipped_empty,
            ),
        )

    async def get(self, project_id: UUID, user_id: UUID) -> Project:
        project = await self.projects.get_for_user(project_id, user_id)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        return project

    async def response(self, project_id: UUID, user_id: UUID) -> ProjectResponse:
        project = await self.get(project_id, user_id)
        return ProjectResponse.from_project(
            project, await self.projects.keyword_count(project.id)
        )

    async def list(
        self,
        user_id: UUID,
        *,
        status: ProjectStatusFilter,
        search: str | None,
        limit: int,
        cursor: str | None,
    ) -> ProjectListResponse:
        selected_status = None if status == "all" else ProjectStatus(status)
        items, has_more = await self.projects.list_for_user(
            user_id,
            status=selected_status,
            search=search.strip() if search and search.strip() else None,
            limit=limit,
            cursor=decode_cursor(cursor),
        )
        next_cursor = (
            encode_cursor(items[-1][0].created_at, items[-1][0].id)
            if has_more and items
            else None
        )
        return ProjectListResponse(
            items=[ProjectResponse.from_project(item, count) for item, count in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def update(
        self, project_id: UUID, user_id: UUID, data: ProjectUpdate
    ) -> Project:
        values = ProjectUpdateValues()
        fields = data.model_fields_set
        if "name" in fields and data.name is not None:
            values["name"] = normalize_name(data.name)
        if "search_engine" in fields and data.search_engine is not None:
            values["search_engine"] = normalize_search_engine(data.search_engine)
        if "country_code" in fields and data.country_code is not None:
            values["country_code"] = normalize_country_code(data.country_code)
        if "language_code" in fields and data.language_code is not None:
            values["language_code"] = normalize_language_code(data.language_code)
        if "device" in fields and data.device is not None:
            values["device"] = normalize_device(data.device)
        if "location" in fields:
            values["location"] = normalize_location(data.location)
        if "status" in fields and data.status is not None:
            values["status"] = data.status
        await EntitlementService(self.projects.session).project_change(
            user_id, project_id, values.get("device"), values.get("status")
        )
        project = await self.projects.update_for_user(project_id, user_id, values)
        if project is None:
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        logger.info("Project updated", extra={"project_id": str(project.id)})
        return project

    async def update_response(
        self, project_id: UUID, user_id: UUID, data: ProjectUpdate
    ) -> ProjectResponse:
        project = await self.update(project_id, user_id, data)
        return ProjectResponse.from_project(
            project, await self.projects.keyword_count(project.id)
        )

    async def delete(self, project_id: UUID, user_id: UUID) -> None:
        if self.rank_checks and await self.rank_checks.has_for_project(
            project_id, user_id
        ):
            raise AppError(
                409,
                "HISTORY_EXISTS",
                "Archive this Project because ranking history exists.",
            )
        if not await self.projects.delete_for_user(project_id, user_id):
            raise AppError(404, "PROJECT_NOT_FOUND", "Project not found.")
        logger.info("Project deleted", extra={"project_id": str(project_id)})
