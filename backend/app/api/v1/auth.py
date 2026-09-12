from fastapi import APIRouter, Request, Response

from app.core.auth_http import clear_refresh_cookie, set_refresh_cookie
from app.dependencies.auth import AppSettings, Authentication
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, SessionRequest
from app.schemas.health import ErrorResponse, HealthResponse

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.post("/register", status_code=201)
async def register(
    data: RegisterRequest,
    response: Response,
    auth: Authentication,
    settings: AppSettings,
) -> AuthResponse:
    issued = await auth.register(data)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return issued.response


@router.post("/login")
async def login(
    data: LoginRequest, response: Response, auth: Authentication, settings: AppSettings
) -> AuthResponse:
    issued = await auth.login(data)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return issued.response


@router.post(
    "/refresh",
    description=(
        "Send the HttpOnly refresh cookie and Content-Type: application/json. "
        "Rotates the cookie; never submit a token in the body."
    ),
)
async def refresh(
    request: Request,
    response: Response,
    auth: Authentication,
    settings: AppSettings,
    body: SessionRequest | None = None,
) -> AuthResponse:
    issued = await auth.refresh(request.cookies.get(settings.auth_cookie_name))
    set_refresh_cookie(response, issued.refresh_token, settings)
    return issued.response


@router.post(
    "/logout",
    description=(
        "Revokes the current refresh cookie and expires it. "
        "Requires Content-Type: application/json. Idempotent."
    ),
)
async def logout(
    request: Request,
    response: Response,
    auth: Authentication,
    settings: AppSettings,
    body: SessionRequest | None = None,
) -> HealthResponse:
    await auth.logout(request.cookies.get(settings.auth_cookie_name))
    clear_refresh_cookie(response, settings)
    return HealthResponse()
