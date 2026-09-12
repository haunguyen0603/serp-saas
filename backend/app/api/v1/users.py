from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.schemas.health import ErrorResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}}
)
async def current_user(user: CurrentUser) -> UserResponse:
    return UserResponse.from_user(user)
