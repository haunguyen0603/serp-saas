from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dependencies.auth import DBSession
from app.repositories.keyword import KeywordRepository
from app.repositories.project import ProjectRepository
from app.repositories.rank_check import RankCheckRepository
from app.repositories.ranking import RankingRepository
from app.repositories.tracked_domain import TrackedDomainRepository
from app.repositories.tracked_site import TrackedSiteRepository
from app.services.domain_matching import DomainMatcher
from app.services.keywords import KeywordService
from app.services.projects import ProjectService
from app.services.rank_checks import RankCheckExecutionService, RankCheckQueryService
from app.services.serp.factory import get_provider_router
from app.services.serp.router import ProviderRouter
from app.services.tracked_sites import TrackedSiteService


def get_project_service(session: DBSession) -> ProjectService:
    return ProjectService(
        ProjectRepository(session),
        KeywordRepository(session),
        RankCheckRepository(session),
    )


def get_keyword_service(session: DBSession) -> KeywordService:
    return KeywordService(
        KeywordRepository(session),
        ProjectRepository(session),
        RankCheckRepository(session),
    )


def get_tracked_site_service(session: DBSession) -> TrackedSiteService:
    return TrackedSiteService(
        TrackedSiteRepository(session),
        TrackedDomainRepository(session),
        RankingRepository(session),
    )


def get_serp_provider_dependency(request: Request) -> ProviderRouter:
    return get_provider_router(
        request.app.state.settings, request.app.state.session_factory
    )


ProviderRouterDependency = Annotated[
    ProviderRouter, Depends(get_serp_provider_dependency)
]


def get_rank_check_execution_service(
    request: Request, provider: ProviderRouterDependency
) -> RankCheckExecutionService:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return RankCheckExecutionService(
        factory, provider, request.app.state.settings, DomainMatcher()
    )


def get_rank_check_query_service(session: DBSession) -> RankCheckQueryService:
    return RankCheckQueryService(session)


Projects = Annotated[ProjectService, Depends(get_project_service)]
Keywords = Annotated[KeywordService, Depends(get_keyword_service)]
TrackedSites = Annotated[TrackedSiteService, Depends(get_tracked_site_service)]
RankCheckExecution = Annotated[
    RankCheckExecutionService, Depends(get_rank_check_execution_service)
]
RankCheckQueries = Annotated[
    RankCheckQueryService, Depends(get_rank_check_query_service)
]
