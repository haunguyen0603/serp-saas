from typing import Any

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser, DBSession
from app.services.overview import OverviewService

router = APIRouter(tags=["overview"])


@router.get("/overview")
async def overview(user: CurrentUser, session: DBSession) -> dict[str, Any]:
    return await OverviewService(session).summary(user.id)
