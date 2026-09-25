from datetime import datetime
from typing import Literal, TypedDict, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.keyword import Keyword
from app.models.keyword_organization import KeywordTagAssignment
from app.models.project import Project


class KeywordValues(TypedDict):
    keyword: str
    keyword_normalized: str


class KeywordUpdateValues(TypedDict, total=False):
    keyword: str
    keyword_normalized: str
    active: bool


class KeywordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_project(
        self, project_id: UUID, values: KeywordValues
    ) -> Keyword | None:
        statement = (
            insert(Keyword)
            .values(project_id=project_id, **values)
            .on_conflict_do_nothing(constraint="uq_keywords_project_keyword_normalized")
            .returning(Keyword)
        )
        return cast(Keyword | None, await self.session.scalar(statement))

    async def bulk_create_for_project(
        self, project_id: UUID, values: list[KeywordValues]
    ) -> list[Keyword]:
        if not values:
            return []
        rows = [{"project_id": project_id, **value} for value in values]
        statement = (
            insert(Keyword)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_keywords_project_keyword_normalized")
            .returning(Keyword)
        )
        return list((await self.session.scalars(statement)).all())

    async def get_for_user_project(
        self, keyword_id: UUID, project_id: UUID, user_id: UUID
    ) -> Keyword | None:
        return cast(
            Keyword | None,
            await self.session.scalar(
                select(Keyword)
                .options(selectinload(Keyword.group), selectinload(Keyword.tags))
                .execution_options(populate_existing=True)
                .join(Project, Project.id == Keyword.project_id)
                .where(
                    Keyword.id == keyword_id,
                    Keyword.project_id == project_id,
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            ),
        )

    async def list_for_user_project(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        search: str | None,
        active: bool | None,
        group_filter: UUID | Literal["none"] | None,
        tag_ids: set[UUID],
        tag_match: Literal["any", "all"],
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> tuple[list[Keyword], bool]:
        statement = (
            select(Keyword)
            .join(Project, Project.id == Keyword.project_id)
            .where(
                Keyword.project_id == project_id,
                Project.id == project_id,
                Project.user_id == user_id,
            )
        )
        if search:
            statement = statement.where(
                Keyword.keyword.icontains(search, autoescape=True)
            )
        if active is not None:
            statement = statement.where(Keyword.active == active)
        if group_filter == "none":
            statement = statement.where(Keyword.keyword_group_id.is_(None))
        elif group_filter is not None:
            statement = statement.where(Keyword.keyword_group_id == group_filter)
        if tag_ids:
            matching_tags = (
                select(func.count(func.distinct(KeywordTagAssignment.tag_id)))
                .where(
                    KeywordTagAssignment.project_id == project_id,
                    KeywordTagAssignment.keyword_id == Keyword.id,
                    KeywordTagAssignment.tag_id.in_(tag_ids),
                )
                .correlate(Keyword)
                .scalar_subquery()
            )
            statement = statement.where(
                matching_tags >= 1
                if tag_match == "any"
                else matching_tags == len(tag_ids)
            )
        if cursor:
            created_at, item_id = cursor
            statement = statement.where(
                or_(
                    Keyword.created_at < created_at,
                    and_(Keyword.created_at == created_at, Keyword.id < item_id),
                )
            )
        statement = (
            statement.options(selectinload(Keyword.group), selectinload(Keyword.tags))
            .order_by(Keyword.created_at.desc(), Keyword.id.desc())
            .limit(limit + 1)
        )
        items = list((await self.session.scalars(statement)).all())
        return items[:limit], len(items) > limit

    async def list_active_for_user_project(
        self,
        project_id: UUID,
        user_id: UUID,
        *,
        keyword_ids: list[UUID] | None = None,
    ) -> list[Keyword]:
        statement = (
            select(Keyword)
            .join(Project, Project.id == Keyword.project_id)
            .where(
                Keyword.project_id == project_id,
                Keyword.active.is_(True),
                Project.user_id == user_id,
            )
            .order_by(Keyword.created_at, Keyword.id)
        )
        if keyword_ids is not None:
            statement = statement.where(Keyword.id.in_(keyword_ids))
        return list((await self.session.scalars(statement)).all())

    async def update_for_user_project(
        self,
        keyword_id: UUID,
        project_id: UUID,
        user_id: UUID,
        values: KeywordUpdateValues,
    ) -> Keyword | None:
        keyword = await self.get_for_user_project(keyword_id, project_id, user_id)
        if keyword is None:
            return None
        if "keyword" in values:
            keyword.keyword = values["keyword"]
            keyword.keyword_normalized = values["keyword_normalized"]
        if "active" in values:
            keyword.active = values["active"]
        await self.session.flush()
        await self.session.refresh(keyword)
        return keyword

    async def delete_for_user_project(
        self, keyword_id: UUID, project_id: UUID, user_id: UUID
    ) -> bool:
        keyword = await self.get_for_user_project(keyword_id, project_id, user_id)
        if keyword is None:
            return False
        await self.session.delete(keyword)
        await self.session.flush()
        return True
