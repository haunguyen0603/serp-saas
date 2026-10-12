from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.competitor_analytics import router as competitor_analytics_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.keyword_organization import router as keyword_organization_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.overview import router as overview_router
from app.api.v1.payments import router as payments_router
from app.api.v1.projects import router as projects_router
from app.api.v1.rank_batches import router as rank_batches_router
from app.api.v1.rank_checks import router as rank_checks_router
from app.api.v1.ranking_explorer import router as ranking_explorer_router
from app.api.v1.rankings import router as rankings_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tracked_sites import router as tracked_sites_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")

router.include_router(rank_batches_router)
router.include_router(analytics_router)
router.include_router(ranking_explorer_router)
router.include_router(competitor_analytics_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(rank_checks_router)
router.include_router(rankings_router)
router.include_router(keywords_router)
router.include_router(keyword_organization_router)
router.include_router(reports_router)
router.include_router(tracked_sites_router)

router.include_router(billing_router)

router.include_router(overview_router)

router.include_router(payments_router)
router.include_router(invoices_router)
