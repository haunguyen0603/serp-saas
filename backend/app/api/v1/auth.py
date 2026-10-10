from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.core.auth_http import clear_refresh_cookie, set_refresh_cookie
from app.dependencies.auth import (
    AppSettings,
    AuthenticatedUser,
    Authentication,
    DBSession,
)
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, SessionRequest
from app.schemas.email_verification import (
    VerificationStatus,
    VerifiedEmailResponse,
    VerifyEmailRequest,
)
from app.schemas.health import ErrorResponse, HealthResponse
from app.schemas.password import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.email_verification import (
    EmailVerificationService,
    deliver_verification_email,
)
from app.services.password import PasswordService, deliver_password_reset_email

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


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    session: DBSession,
    settings: AppSettings,
    request: Request,
    background: BackgroundTasks,
) -> HealthResponse:
    pending = await PasswordService(session, settings).request_reset(str(data.email))
    if pending is not None:
        background.add_task(
            deliver_password_reset_email, pending, request.app.state.auth_email_sender
        )
    return HealthResponse()


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    session: DBSession,
    settings: AppSettings,
    response: Response,
) -> HealthResponse:
    await PasswordService(session, settings).reset(
        data.token.get_secret_value(), data.new_password.get_secret_value()
    )
    clear_refresh_cookie(response, settings)
    return HealthResponse()


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: AuthenticatedUser,
    session: DBSession,
    settings: AppSettings,
    auth: Authentication,
    response: Response,
) -> AuthResponse:
    changed = await PasswordService(session, settings).change(
        user,
        data.current_password.get_secret_value(),
        data.new_password.get_secret_value(),
    )
    issued = await auth.issue_session(changed)
    set_refresh_cookie(response, issued.refresh_token, settings)
    return issued.response


@router.post("/register", status_code=201)
async def register(
    data: RegisterRequest,
    response: Response,
    auth: Authentication,
    settings: AppSettings,
    request: Request,
    background: BackgroundTasks,
) -> AuthResponse:
    issued = await auth.register(data)
    set_refresh_cookie(response, issued.refresh_token, settings)
    if issued.verification is not None:
        background.add_task(
            deliver_verification_email,
            issued.verification,
            request.app.state.auth_email_sender,
            request.app.state.session_factory,
        )
    return issued.response


@router.get("/email-verification")
async def verification_status(
    user: AuthenticatedUser, session: DBSession, settings: AppSettings
) -> VerificationStatus:
    return await EmailVerificationService(session, settings).status(user)


@router.post("/email-verification/resend")
async def resend_verification(
    user: AuthenticatedUser,
    session: DBSession,
    settings: AppSettings,
    request: Request,
    background: BackgroundTasks,
) -> VerificationStatus:
    service = EmailVerificationService(session, settings)
    pending = await service.request(user.id)
    if pending is not None:
        background.add_task(
            deliver_verification_email,
            pending,
            request.app.state.auth_email_sender,
            request.app.state.session_factory,
        )
    return await service.status(user)


@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailRequest, session: DBSession, settings: AppSettings
) -> VerifiedEmailResponse:
    user = await EmailVerificationService(session, settings).verify(
        data.token.get_secret_value()
    )
    return VerifiedEmailResponse(user_id=user.id)


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
