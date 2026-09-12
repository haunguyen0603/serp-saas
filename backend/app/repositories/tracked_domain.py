from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite, TrackedSiteStatus


class TrackedDomainValues(TypedDict):
    domain: str
    is_primary: bool
    active: bool


class TrackedDomainRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_site(
        self,
        site_id: UUID,
        user_id: UUID,
        *,
        domain: str,
        is_primary: bool,
    ) -> TrackedDomain | None:
        statement = (
            insert(TrackedDomain)
            .values(
                tracked_site_id=site_id,
                user_id=user_id,
                domain=domain,
                is_primary=is_primary,
                active=True,
            )
            .on_conflict_do_nothing(constraint="uq_tracked_domains_user_domain")
            .returning(TrackedDomain)
        )
        return cast(TrackedDomain | None, await self.session.scalar(statement))

    async def bulk_create_for_site(
        self,
        site_id: UUID,
        user_id: UUID,
        values: list[TrackedDomainValues],
    ) -> list[TrackedDomain]:
        rows = [
            {"tracked_site_id": site_id, "user_id": user_id, **value}
            for value in values
        ]
        if not rows:
            return []
        statement = (
            insert(TrackedDomain)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_tracked_domains_user_domain")
            .returning(TrackedDomain)
        )
        return list((await self.session.scalars(statement)).all())

    async def list_for_sites(
        self, site_ids: list[UUID], user_id: UUID
    ) -> list[TrackedDomain]:
        if not site_ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(TrackedDomain).where(
                        TrackedDomain.tracked_site_id.in_(site_ids),
                        TrackedDomain.user_id == user_id,
                    )
                )
            ).all()
        )

    async def list_for_site(self, site_id: UUID, user_id: UUID) -> list[TrackedDomain]:
        return await self.list_for_sites([site_id], user_id)

    async def list_active_for_matching(
        self, user_id: UUID
    ) -> list[tuple[TrackedDomain, TrackedSite]]:
        statement = (
            select(TrackedDomain, TrackedSite)
            .join(
                TrackedSite,
                (TrackedSite.id == TrackedDomain.tracked_site_id)
                & (TrackedSite.user_id == TrackedDomain.user_id),
            )
            .where(
                TrackedDomain.user_id == user_id,
                TrackedDomain.active.is_(True),
                TrackedSite.status == TrackedSiteStatus.ACTIVE,
            )
        )
        return list((await self.session.execute(statement)).tuples().all())

    async def get_for_user_site(
        self, domain_id: UUID, site_id: UUID, user_id: UUID
    ) -> TrackedDomain | None:
        return cast(
            TrackedDomain | None,
            await self.session.scalar(
                select(TrackedDomain)
                .join(
                    TrackedSite,
                    (TrackedSite.id == TrackedDomain.tracked_site_id)
                    & (TrackedSite.user_id == TrackedDomain.user_id),
                )
                .where(
                    TrackedDomain.id == domain_id,
                    TrackedDomain.tracked_site_id == site_id,
                    TrackedDomain.user_id == user_id,
                    TrackedSite.id == site_id,
                    TrackedSite.user_id == user_id,
                )
            ),
        )

    async def set_primary(
        self, domain_id: UUID, site_id: UUID, user_id: UUID
    ) -> TrackedDomain | None:
        domain = await self.get_for_user_site(domain_id, site_id, user_id)
        if domain is None:
            return None
        await self.session.execute(
            update(TrackedDomain)
            .where(
                TrackedDomain.tracked_site_id == site_id,
                TrackedDomain.user_id == user_id,
                TrackedDomain.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        await self.session.execute(
            update(TrackedDomain)
            .where(
                TrackedDomain.id == domain_id,
                TrackedDomain.tracked_site_id == site_id,
                TrackedDomain.user_id == user_id,
            )
            .values(is_primary=True, active=True)
        )
        await self.session.flush()
        self.session.expire(domain)
        await self.session.refresh(domain)
        return domain

    async def set_active(self, domain: TrackedDomain, active: bool) -> TrackedDomain:
        domain.active = active
        await self.session.flush()
        await self.session.refresh(domain)
        return domain

    async def delete(self, domain: TrackedDomain) -> None:
        await self.session.delete(domain)
        await self.session.flush()
