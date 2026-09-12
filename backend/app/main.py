import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from app.api.router import router
from app.core.auth_http import AuthHTTPMiddleware
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.redis import create_redis_client
from app.core.security import hash_password
from app.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        client = create_redis_client(settings)
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = client
        try:
            app.state.dummy_password_hash = await run_in_threadpool(
                hash_password, secrets.token_urlsafe(32)
            )
            yield
        finally:
            try:
                await client.aclose()
            finally:
                await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=False,
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.state.settings = settings
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/docs")

    app.add_middleware(AuthHTTPMiddleware, settings=settings)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    return app
