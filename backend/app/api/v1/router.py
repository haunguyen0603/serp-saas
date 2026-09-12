from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.projects import router as projects_router
from app.api.v1.rank_checks import router as rank_checks_router
from app.api.v1.rankings import router as rankings_router
from app.api.v1.tracked_sites import router as tracked_sites_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(rank_checks_router)
router.include_router(rankings_router)
router.include_router(keywords_router)
router.include_router(tracked_sites_router)
