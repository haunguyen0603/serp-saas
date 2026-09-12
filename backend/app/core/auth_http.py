from fastapi import Response
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import error_response

COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.auth_cookie_name,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


class AuthHTTPMiddleware:
    """No-store on all auth outcomes; reject cross-origin/simple-form mutations."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not (
            scope["path"].startswith("/api/v1/auth/")
            or scope["path"] == "/api/v1/users/me"
        ):
            await self.app(scope, receive, send)
            return

        async def no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value)
                    for key, value in message["headers"]
                    if key.lower() != b"cache-control"
                ]
                message["headers"].append((b"cache-control", b"no-store"))
            await send(message)

        if scope["method"] == "POST":
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            same_origin = f"{scope['scheme']}://{headers.get('host', '')}"
            if origin is not None and origin not in [
                *self.settings.cors_origins,
                same_origin,
            ]:
                await error_response(
                    403, "UNTRUSTED_ORIGIN", "Request origin is not allowed."
                )(scope, receive, no_store)
                return
            if (
                headers.get("content-type", "").split(";", 1)[0].strip().lower()
                != "application/json"
            ):
                await error_response(
                    415,
                    "JSON_REQUIRED",
                    "Authentication requests require application/json.",
                )(scope, receive, no_store)
                return
        await self.app(scope, receive, no_store)
