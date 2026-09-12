import logging
from collections import defaultdict
from uuid import UUID

from app.core.errors import AppError
from app.models.tracked_domain import TrackedDomain
from app.models.tracked_site import TrackedSite, TrackedSiteStatus
from app.repositories.ranking import RankingRepository
from app.repositories.tracked_domain import (
    TrackedDomainRepository,
    TrackedDomainValues,
)
from app.repositories.tracked_site import (
    TrackedSiteRepository,
    TrackedSiteUpdateValues,
)
from app.schemas.tracked_site import (
    TrackedDomainCreate,
    TrackedDomainResponse,
    TrackedDomainUpdate,
    TrackedSiteCreate,
    TrackedSiteListResponse,
    TrackedSiteResponse,
    TrackedSiteStatusFilter,
    TrackedSiteUpdate,
)
from app.services.normalization import (
    decode_cursor,
    encode_cursor,
    normalize_domain,
    normalize_tracked_site_name,
)

logger = logging.getLogger(__name__)


class TrackedSiteService:
    def __init__(
        self,
        sites: TrackedSiteRepository,
        domains: TrackedDomainRepository,
        rankings: RankingRepository | None = None,
    ) -> None:
        self.sites = sites
        self.domains = domains
        self.rankings = rankings

    async def _site(
        self, site_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> TrackedSite:
        site = await self.sites.get_for_user(site_id, user_id, for_update=for_update)
        if site is None:
            raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
        return site

    async def _response(self, site: TrackedSite) -> TrackedSiteResponse:
        return TrackedSiteResponse.from_site(
            site, await self.domains.list_for_site(site.id, site.user_id)
        )

    async def create(
        self, user_id: UUID, data: TrackedSiteCreate
    ) -> TrackedSiteResponse:
        primary = normalize_domain(data.primary_domain)
        normalized = [primary, *(normalize_domain(value) for value in data.aliases)]
        unique = list(dict.fromkeys(normalized))
        site = await self.sites.create_for_user(
            user_id, normalize_tracked_site_name(data.name)
        )
        values = [
            TrackedDomainValues(
                domain=domain, is_primary=domain == primary, active=True
            )
            for domain in unique
        ]
        created = await self.domains.bulk_create_for_site(site.id, user_id, values)
        if len(created) != len(unique):
            raise AppError(409, "DOMAIN_ALREADY_TRACKED", "Domain is already tracked.")
        logger.info("Tracked Site created", extra={"tracked_site_id": str(site.id)})
        return TrackedSiteResponse.from_site(site, created)

    async def get(self, site_id: UUID, user_id: UUID) -> TrackedSiteResponse:
        return await self._response(await self._site(site_id, user_id))

    async def list(
        self,
        user_id: UUID,
        *,
        status: TrackedSiteStatusFilter,
        search: str | None,
        limit: int,
        cursor: str | None,
    ) -> TrackedSiteListResponse:
        selected_status = None if status == "all" else TrackedSiteStatus(status)
        sites, has_more = await self.sites.list_for_user(
            user_id,
            status=selected_status,
            search=search.strip() if search and search.strip() else None,
            limit=limit,
            cursor=decode_cursor(cursor),
        )
        domain_rows = await self.domains.list_for_sites(
            [site.id for site in sites], user_id
        )
        by_site: dict[UUID, list[TrackedDomain]] = defaultdict(list)
        for domain in domain_rows:
            by_site[domain.tracked_site_id].append(domain)
        next_cursor = (
            encode_cursor(sites[-1].created_at, sites[-1].id)
            if has_more and sites
            else None
        )
        return TrackedSiteListResponse(
            items=[
                TrackedSiteResponse.from_site(site, by_site[site.id]) for site in sites
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def update(
        self, site_id: UUID, user_id: UUID, data: TrackedSiteUpdate
    ) -> TrackedSiteResponse:
        site = await self._site(site_id, user_id, for_update=True)
        values = TrackedSiteUpdateValues()
        if "name" in data.model_fields_set and data.name is not None:
            values["name"] = normalize_tracked_site_name(data.name)
        if "status" in data.model_fields_set and data.status is not None:
            if data.status is TrackedSiteStatus.ACTIVE:
                domains = await self.domains.list_for_site(site.id, user_id)
                if not any(domain.is_primary and domain.active for domain in domains):
                    raise AppError(
                        409,
                        "PRIMARY_DOMAIN_REQUIRED",
                        "An active Tracked Site requires a primary domain.",
                    )
            values["status"] = data.status
        updated = await self.sites.update_for_user(site.id, user_id, values)
        assert updated is not None
        logger.info("Tracked Site updated", extra={"tracked_site_id": str(site.id)})
        return await self._response(updated)

    async def delete(self, site_id: UUID, user_id: UUID) -> None:
        site = await self._site(site_id, user_id)
        if self.rankings and await self.rankings.has_for_site(site.id):
            raise AppError(
                409,
                "HISTORY_EXISTS",
                "Archive this Tracked Site because ranking history exists.",
            )
        if not await self.sites.delete_for_user(site_id, user_id):
            raise AppError(404, "TRACKED_SITE_NOT_FOUND", "Tracked Site not found.")
        logger.info("Tracked Site deleted", extra={"tracked_site_id": str(site_id)})

    async def add_domain(
        self, site_id: UUID, user_id: UUID, data: TrackedDomainCreate
    ) -> TrackedDomainResponse:
        await self._site(site_id, user_id, for_update=True)
        domain = await self.domains.create_for_site(
            site_id,
            user_id,
            domain=normalize_domain(data.domain),
            is_primary=False,
        )
        if domain is None:
            raise AppError(409, "DOMAIN_ALREADY_TRACKED", "Domain is already tracked.")
        if data.make_primary:
            promoted = await self.domains.set_primary(domain.id, site_id, user_id)
            assert promoted is not None
            domain = promoted
        logger.info("Tracked Domain created", extra={"tracked_site_id": str(site_id)})
        return TrackedDomainResponse.from_domain(domain)

    async def update_domain(
        self,
        domain_id: UUID,
        site_id: UUID,
        user_id: UUID,
        data: TrackedDomainUpdate,
    ) -> TrackedDomainResponse:
        await self._site(site_id, user_id, for_update=True)
        domain = await self.domains.get_for_user_site(domain_id, site_id, user_id)
        if domain is None:
            raise AppError(404, "TRACKED_DOMAIN_NOT_FOUND", "Tracked Domain not found.")
        if data.is_primary is True and data.active is False:
            raise AppError(
                409,
                "PRIMARY_DOMAIN_MUST_BE_ACTIVE",
                "The primary domain must be active.",
            )
        if data.is_primary is False and domain.is_primary:
            raise AppError(
                409,
                "PRIMARY_DOMAIN_REPLACEMENT_REQUIRED",
                "Promote another domain before replacing the primary domain.",
            )
        if data.active is False and domain.is_primary:
            raise AppError(
                409,
                "PRIMARY_DOMAIN_MUST_BE_ACTIVE",
                "The primary domain must be active.",
            )
        if data.is_primary is True:
            promoted = await self.domains.set_primary(domain.id, site_id, user_id)
            assert promoted is not None
            domain = promoted
        elif data.active is not None:
            domain = await self.domains.set_active(domain, data.active)
        logger.info("Tracked Domain updated", extra={"tracked_site_id": str(site_id)})
        return TrackedDomainResponse.from_domain(domain)

    async def delete_domain(
        self, domain_id: UUID, site_id: UUID, user_id: UUID
    ) -> None:
        site = await self._site(site_id, user_id, for_update=True)
        domain = await self.domains.get_for_user_site(domain_id, site_id, user_id)
        if domain is None:
            raise AppError(404, "TRACKED_DOMAIN_NOT_FOUND", "Tracked Domain not found.")
        all_domains = await self.domains.list_for_site(site_id, user_id)
        if domain.is_primary and len(all_domains) > 1:
            raise AppError(
                409,
                "PRIMARY_DOMAIN_REPLACEMENT_REQUIRED",
                "Promote another domain before deleting the primary domain.",
            )
        if domain.is_primary and site.status is TrackedSiteStatus.ACTIVE:
            raise AppError(
                409,
                "PRIMARY_DOMAIN_REQUIRED",
                "An active Tracked Site requires a primary domain.",
            )
        if self.rankings and await self.rankings.has_for_domain(domain.id):
            raise AppError(
                409,
                "HISTORY_EXISTS",
                "Deactivate this Domain because ranking history exists.",
            )
        await self.domains.delete(domain)
        logger.info("Tracked Domain deleted", extra={"tracked_site_id": str(site_id)})
