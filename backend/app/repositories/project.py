from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.models.project import Project, ProjectStatus


class ProjectUpdateValues(TypedDict, total=False):
    name: str
    search_engine: str
    country_code: str
    language_code: str
    device: str
    location: str | None
    status: ProjectStatus


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_user(
        self,
        user_id: UUID,
        *,
        name: str,
        search_engine: str,
        country_code: str,
        language_code: str,
        device: str,
        location: str | None,
    ) -> Project:
        project = Project(
            user_id=user_id,
            name=name,
            search_engine=search_engine,
            country_code=country_code,
            language_code=language_code,
            device=device,
            location=location,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        return cast(
            Project | None,
            await self.session.scalar(
                select(Project).where(
                    Project.id == project_id, Project.user_id == user_id
                )
            ),
        )

    async def keyword_count(self, project_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Keyword.id)).where(Keyword.project_id == project_id)
            )
            or 0
        )

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: ProjectStatus | None,
        search: str | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> tuple[list[tuple[Project, int]], bool]:
        count = (
            select(func.count(Keyword.id))
            .where(Keyword.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        statement = select(Project, count).where(Project.user_id == user_id)
        if status is not None:
            statement = statement.where(Project.status == status)
        if search:
            statement = statement.where(Project.name.icontains(search, autoescape=True))
        if cursor:
            created_at, item_id = cursor
            statement = statement.where(
                or_(
                    Project.created_at < created_at,
                    and_(Project.created_at == created_at, Project.id < item_id),
                )
            )
        statement = statement.order_by(
            Project.created_at.desc(), Project.id.desc()
        ).limit(limit + 1)
        rows = list((await self.session.execute(statement)).all())
        items = [(row[0], int(row[1])) for row in rows[:limit]]
        return items, len(rows) > limit

    async def update_for_user(
        self, project_id: UUID, user_id: UUID, values: ProjectUpdateValues
    ) -> Project | None:
        project = await self.get_for_user(project_id, user_id)
        if project is None:
            return None
        for field in (
            "name",
            "search_engine",
            "country_code",
            "language_code",
            "device",
            "location",
            "status",
        ):
            if field in values:
                setattr(project, field, values[field])
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete_for_user(self, project_id: UUID, user_id: UUID) -> bool:
        project = await self.get_for_user(project_id, user_id)
        if project is None:
            return False
        await self.session.delete(project)
        await self.session.flush()
        return True
