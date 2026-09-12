from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracked_site import TrackedSite, TrackedSiteStatus


class TrackedSiteUpdateValues(TypedDict, total=False):
    name: str
    status: TrackedSiteStatus


class TrackedSiteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_user(self, user_id: UUID, name: str) -> TrackedSite:
        site = TrackedSite(user_id=user_id, name=name)
        self.session.add(site)
        await self.session.flush()
        await self.session.refresh(site)
        return site

    async def get_for_user(
        self, site_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> TrackedSite | None:
        statement = select(TrackedSite).where(
            TrackedSite.id == site_id, TrackedSite.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(TrackedSite | None, await self.session.scalar(statement))

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: TrackedSiteStatus | None,
        search: str | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> tuple[list[TrackedSite], bool]:
        statement = select(TrackedSite).where(TrackedSite.user_id == user_id)
        if status is not None:
            statement = statement.where(TrackedSite.status == status)
        if search:
            statement = statement.where(
                TrackedSite.name.icontains(search, autoescape=True)
            )
        if cursor:
            created_at, item_id = cursor
            statement = statement.where(
                or_(
                    TrackedSite.created_at < created_at,
                    and_(
                        TrackedSite.created_at == created_at,
                        TrackedSite.id < item_id,
                    ),
                )
            )
        statement = statement.order_by(
            TrackedSite.created_at.desc(), TrackedSite.id.desc()
        ).limit(limit + 1)
        items = list((await self.session.scalars(statement)).all())
        return items[:limit], len(items) > limit

    async def update_for_user(
        self, site_id: UUID, user_id: UUID, values: TrackedSiteUpdateValues
    ) -> TrackedSite | None:
        site = await self.get_for_user(site_id, user_id, for_update=True)
        if site is None:
            return None
        if "name" in values:
            site.name = values["name"]
        if "status" in values:
            site.status = values["status"]
        await self.session.flush()
        await self.session.refresh(site)
        return site

    async def delete_for_user(self, site_id: UUID, user_id: UUID) -> bool:
        site = await self.get_for_user(site_id, user_id, for_update=True)
        if site is None:
            return False
        await self.session.delete(site)
        await self.session.flush()
        return True
