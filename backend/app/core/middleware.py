import logging
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = perf_counter()
        status = 500
        started = False

        async def capture(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                status = message["status"]
                started = True
            await send(message)

        try:
            await self.app(scope, receive, capture)
        except Exception:
            logger.error("Unhandled request failure")
            if not started:
                await error_response(
                    500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred."
                )(scope, receive, capture)
        finally:
            logger.info(
                "HTTP request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status,
                    "duration": round(perf_counter() - start, 6),
                },
            )
