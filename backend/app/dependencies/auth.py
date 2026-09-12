from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.users import UserService

DBSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_auth_service(
    request: Request, session: DBSession, settings: AppSettings
) -> AuthService:
    return AuthService(
        UserRepository(session),
        RefreshTokenRepository(session),
        settings,
        request.app.state.dummy_password_hash,
    )


Authentication = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    session: DBSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise AppError(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
    user_id = decode_access_token(credentials.credentials, settings)
    return await UserService(UserRepository(session)).current_user(user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]
