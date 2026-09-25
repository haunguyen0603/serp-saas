from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.models.keyword_organization import (
    KeywordGroup,
    KeywordTag,
    KeywordTagAssignment,
)
from app.models.project import Project


@dataclass(frozen=True)
class OrganizationCatalogRow:
    entity: KeywordGroup | KeywordTag
    active_keyword_count: int


class KeywordOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_groups(
        self, project_id: UUID, user_id: UUID
    ) -> list[OrganizationCatalogRow]:
        count = (
            select(func.count(Keyword.id))
            .where(
                Keyword.project_id == project_id,
                Keyword.keyword_group_id == KeywordGroup.id,
                Keyword.active.is_(True),
            )
            .correlate(KeywordGroup)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(KeywordGroup, count)
                .join(Project, Project.id == KeywordGroup.project_id)
                .where(
                    KeywordGroup.project_id == project_id,
                    Project.user_id == user_id,
                )
                .order_by(KeywordGroup.normalized_name, KeywordGroup.id)
            )
        ).all()
        return [OrganizationCatalogRow(row[0], int(row[1])) for row in rows]

    async def list_tags(
        self, project_id: UUID, user_id: UUID
    ) -> list[OrganizationCatalogRow]:
        count = (
            select(func.count(KeywordTagAssignment.keyword_id))
            .join(
                Keyword,
                Keyword.id == KeywordTagAssignment.keyword_id,
            )
            .where(
                KeywordTagAssignment.project_id == project_id,
                KeywordTagAssignment.tag_id == KeywordTag.id,
                Keyword.active.is_(True),
            )
            .correlate(KeywordTag)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(KeywordTag, count)
                .join(Project, Project.id == KeywordTag.project_id)
                .where(
                    KeywordTag.project_id == project_id,
                    Project.user_id == user_id,
                )
                .order_by(KeywordTag.normalized_name, KeywordTag.id)
            )
        ).all()
        return [OrganizationCatalogRow(row[0], int(row[1])) for row in rows]

    async def get_group(
        self, project_id: UUID, user_id: UUID, group_id: UUID
    ) -> KeywordGroup | None:
        return cast(
            KeywordGroup | None,
            await self.session.scalar(
                select(KeywordGroup)
                .join(Project, Project.id == KeywordGroup.project_id)
                .where(
                    KeywordGroup.id == group_id,
                    KeywordGroup.project_id == project_id,
                    Project.user_id == user_id,
                )
            ),
        )

    async def get_tag(
        self, project_id: UUID, user_id: UUID, tag_id: UUID
    ) -> KeywordTag | None:
        return cast(
            KeywordTag | None,
            await self.session.scalar(
                select(KeywordTag)
                .join(Project, Project.id == KeywordTag.project_id)
                .where(
                    KeywordTag.id == tag_id,
                    KeywordTag.project_id == project_id,
                    Project.user_id == user_id,
                )
            ),
        )

    async def groups_for_project(
        self, project_id: UUID, group_ids: set[UUID]
    ) -> list[KeywordGroup]:
        if not group_ids:
            return []
        return list(
            await self.session.scalars(
                select(KeywordGroup).where(
                    KeywordGroup.project_id == project_id,
                    KeywordGroup.id.in_(group_ids),
                )
            )
        )

    async def tags_for_project(
        self, project_id: UUID, tag_ids: set[UUID]
    ) -> list[KeywordTag]:
        if not tag_ids:
            return []
        return list(
            await self.session.scalars(
                select(KeywordTag).where(
                    KeywordTag.project_id == project_id,
                    KeywordTag.id.in_(tag_ids),
                )
            )
        )

    async def create_group(
        self, project_id: UUID, name: str, normalized_name: str
    ) -> KeywordGroup:
        entity = KeywordGroup(
            project_id=project_id, name=name, normalized_name=normalized_name
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_tag(
        self, project_id: UUID, name: str, normalized_name: str
    ) -> KeywordTag:
        entity = KeywordTag(
            project_id=project_id, name=name, normalized_name=normalized_name
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete_group(self, group: KeywordGroup) -> None:
        await self.session.execute(
            update(Keyword)
            .where(
                Keyword.project_id == group.project_id,
                Keyword.keyword_group_id == group.id,
            )
            .values(keyword_group_id=None)
        )
        await self.session.delete(group)
        await self.session.flush()

    async def delete_tag(self, tag: KeywordTag) -> None:
        await self.session.delete(tag)
        await self.session.flush()

    async def keywords_for_update(
        self, project_id: UUID, keyword_ids: set[UUID]
    ) -> list[Keyword]:
        return list(
            await self.session.scalars(
                select(Keyword)
                .where(
                    Keyword.project_id == project_id,
                    Keyword.id.in_(keyword_ids),
                )
                .with_for_update()
            )
        )

    async def replace_keyword_tags(
        self, project_id: UUID, keyword_id: UUID, tag_ids: set[UUID]
    ) -> None:
        await self.session.execute(
            delete(KeywordTagAssignment).where(
                KeywordTagAssignment.project_id == project_id,
                KeywordTagAssignment.keyword_id == keyword_id,
            )
        )
        if tag_ids:
            await self.session.execute(
                insert(KeywordTagAssignment).values(
                    [
                        {
                            "project_id": project_id,
                            "keyword_id": keyword_id,
                            "tag_id": tag_id,
                        }
                        for tag_id in tag_ids
                    ]
                )
            )

    async def bulk_assign_group(
        self, project_id: UUID, keyword_ids: set[UUID], group_id: UUID | None
    ) -> set[UUID]:
        return set(
            await self.session.scalars(
                update(Keyword)
                .where(
                    Keyword.project_id == project_id,
                    Keyword.id.in_(keyword_ids),
                    Keyword.keyword_group_id.is_distinct_from(group_id),
                )
                .values(keyword_group_id=group_id)
                .returning(Keyword.id)
            )
        )

    async def bulk_add_tags(
        self, project_id: UUID, keyword_ids: set[UUID], tag_ids: set[UUID]
    ) -> tuple[set[UUID], int]:
        rows = list(
            (
                await self.session.execute(
                    insert(KeywordTagAssignment)
                    .values(
                        [
                            {
                                "project_id": project_id,
                                "keyword_id": keyword_id,
                                "tag_id": tag_id,
                            }
                            for keyword_id in keyword_ids
                            for tag_id in tag_ids
                        ]
                    )
                    .on_conflict_do_nothing()
                    .returning(
                        KeywordTagAssignment.keyword_id,
                        KeywordTagAssignment.tag_id,
                    )
                )
            ).all()
        )
        return {row.keyword_id for row in rows}, len(rows)

    async def bulk_remove_tags(
        self, project_id: UUID, keyword_ids: set[UUID], tag_ids: set[UUID]
    ) -> tuple[set[UUID], int]:
        rows = list(
            (
                await self.session.execute(
                    delete(KeywordTagAssignment)
                    .where(
                        KeywordTagAssignment.project_id == project_id,
                        KeywordTagAssignment.keyword_id.in_(keyword_ids),
                        KeywordTagAssignment.tag_id.in_(tag_ids),
                    )
                    .returning(
                        KeywordTagAssignment.keyword_id,
                        KeywordTagAssignment.tag_id,
                    )
                )
            ).all()
        )
        return {row.keyword_id for row in rows}, len(rows)

    async def bulk_replace_tags(
        self, project_id: UUID, keyword_ids: set[UUID], tag_ids: set[UUID]
    ) -> tuple[set[UUID], int]:
        existing = list(
            (
                await self.session.execute(
                    select(
                        KeywordTagAssignment.keyword_id,
                        KeywordTagAssignment.tag_id,
                    )
                    .where(
                        KeywordTagAssignment.project_id == project_id,
                        KeywordTagAssignment.keyword_id.in_(keyword_ids),
                    )
                    .with_for_update()
                )
            ).all()
        )
        by_keyword: dict[UUID, set[UUID]] = {item_id: set() for item_id in keyword_ids}
        for row in existing:
            by_keyword[row.keyword_id].add(row.tag_id)
        changed = {
            keyword_id
            for keyword_id, current in by_keyword.items()
            if current != tag_ids
        }
        await self.session.execute(
            delete(KeywordTagAssignment).where(
                KeywordTagAssignment.project_id == project_id,
                KeywordTagAssignment.keyword_id.in_(keyword_ids),
            )
        )
        assignment_count = 0
        if tag_ids:
            values = [
                {
                    "project_id": project_id,
                    "keyword_id": keyword_id,
                    "tag_id": tag_id,
                }
                for keyword_id in keyword_ids
                for tag_id in tag_ids
            ]
            await self.session.execute(insert(KeywordTagAssignment).values(values))
            assignment_count = len(values)
        return changed, assignment_count

    async def bulk_set_active(
        self, project_id: UUID, keyword_ids: set[UUID], active: bool
    ) -> set[UUID]:
        return set(
            await self.session.scalars(
                update(Keyword)
                .where(
                    Keyword.project_id == project_id,
                    Keyword.id.in_(keyword_ids),
                    Keyword.active.is_(not active),
                )
                .values(active=active)
                .returning(Keyword.id)
            )
        )
