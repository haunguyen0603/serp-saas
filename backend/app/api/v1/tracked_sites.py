from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.auth import CurrentUser
from app.dependencies.business import TrackedSites
from app.schemas.health import ErrorResponse
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

router = APIRouter(
    prefix="/tracked-sites",
    tags=["tracked-sites"],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.post("", status_code=201, response_model=TrackedSiteResponse)
async def create_tracked_site(
    data: TrackedSiteCreate, user: CurrentUser, sites: TrackedSites
) -> TrackedSiteResponse:
    return await sites.create(user.id, data)


@router.get("", response_model=TrackedSiteListResponse)
async def list_tracked_sites(
    user: CurrentUser,
    sites: TrackedSites,
    status: TrackedSiteStatusFilter = "active",
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> TrackedSiteListResponse:
    return await sites.list(
        user.id, status=status, search=search, limit=limit, cursor=cursor
    )


@router.get("/{site_id}", response_model=TrackedSiteResponse)
async def get_tracked_site(
    site_id: UUID, user: CurrentUser, sites: TrackedSites
) -> TrackedSiteResponse:
    return await sites.get(site_id, user.id)


@router.patch("/{site_id}", response_model=TrackedSiteResponse)
async def update_tracked_site(
    site_id: UUID,
    data: TrackedSiteUpdate,
    user: CurrentUser,
    sites: TrackedSites,
) -> TrackedSiteResponse:
    return await sites.update(site_id, user.id, data)


@router.delete("/{site_id}", status_code=204)
async def delete_tracked_site(
    site_id: UUID, user: CurrentUser, sites: TrackedSites
) -> Response:
    await sites.delete(site_id, user.id)
    return Response(status_code=204)


@router.post(
    "/{site_id}/domains", status_code=201, response_model=TrackedDomainResponse
)
async def add_tracked_domain(
    site_id: UUID,
    data: TrackedDomainCreate,
    user: CurrentUser,
    sites: TrackedSites,
) -> TrackedDomainResponse:
    return await sites.add_domain(site_id, user.id, data)


@router.patch("/{site_id}/domains/{domain_id}", response_model=TrackedDomainResponse)
async def update_tracked_domain(
    site_id: UUID,
    domain_id: UUID,
    data: TrackedDomainUpdate,
    user: CurrentUser,
    sites: TrackedSites,
) -> TrackedDomainResponse:
    return await sites.update_domain(domain_id, site_id, user.id, data)


@router.delete("/{site_id}/domains/{domain_id}", status_code=204)
async def delete_tracked_domain(
    site_id: UUID,
    domain_id: UUID,
    user: CurrentUser,
    sites: TrackedSites,
) -> Response:
    await sites.delete_domain(domain_id, site_id, user.id)
    return Response(status_code=204)
