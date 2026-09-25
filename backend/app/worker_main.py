"""Private Cloud Run entry point: uvicorn app.worker_main:app --port 8080."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.db.session import create_session_factory
from app.schemas.rank_job import TaskPayload
from app.schemas.report import ReportTaskPayload
from app.services.rank_batches import RankBatchService
from app.services.rank_schedules import RankScheduleService
from app.services.rank_worker import RankCheckWorker
from app.services.report_email import create_report_email_sender
from app.services.report_storage import create_report_storage
from app.services.report_worker import ReportWorker
from app.services.reports import ReportService
from app.services.serp.factory import get_provider_router
from app.services.task_queue import create_task_queue


async def authenticate_internal(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if settings.task_queue_provider == "local" and settings.app_env != "production":
        return
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        raise HTTPException(401, "Service authentication required")
    try:
        claims = await asyncio.to_thread(
            verify_oauth2_token,
            token[7:],
            GoogleRequest(),
            settings.cloud_tasks_worker_url.rstrip("/"),
        )
    except Exception:
        raise HTTPException(401, "Invalid service identity") from None
    expected = (
        settings.cloud_tasks_service_account_email
        if request.url.path.startswith("/internal/tasks/")
        else settings.scheduler_service_account_email
    )
    if claims.get("email") != expected or claims.get("email_verified") is not True:
        raise HTTPException(403, "Service identity is not authorized")


def create_worker_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_async_engine(
            settings.database_url.get_secret_value(),
            pool_size=settings.worker_db_pool_size,
            max_overflow=settings.worker_db_max_overflow,
            pool_pre_ping=True,
            hide_parameters=True,
        )
        app.state.session_factory = create_session_factory(engine)
        app.state.task_queue = create_task_queue(settings)
        app.state.report_storage = create_report_storage(settings)
        app.state.report_email_sender = create_report_email_sender(settings)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    register_error_handlers(app)

    def worker(request: Request) -> RankCheckWorker:
        factory = request.app.state.session_factory
        batches = RankBatchService(factory, settings, create_task_queue(settings))
        return RankCheckWorker(batches, get_provider_router(settings, factory))

    def report_worker(request: Request) -> ReportWorker:
        return ReportWorker(
            ReportService(
                request.app.state.session_factory,
                settings,
                request.app.state.task_queue,
                request.app.state.report_storage,
                request.app.state.report_email_sender,
            )
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db")
    async def db(request: Request) -> dict[str, str]:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.post(
        "/internal/tasks/rank-check", dependencies=[Depends(authenticate_internal)]
    )
    async def run_task(
        payload: TaskPayload, service: Annotated[RankCheckWorker, Depends(worker)]
    ) -> JSONResponse:
        handled = await service.execute(payload.job_id)
        return JSONResponse(
            {"status": "handled" if handled else "retry"},
            status_code=200 if handled else 503,
        )

    @app.post("/internal/tasks/report", dependencies=[Depends(authenticate_internal)])
    async def run_report_task(
        payload: ReportTaskPayload,
        service: Annotated[ReportWorker, Depends(report_worker)],
    ) -> JSONResponse:
        handled = await service.execute(payload.report_id)
        return JSONResponse(
            {"status": "handled" if handled else "retry"},
            status_code=200 if handled else 503,
        )

    @app.post(
        "/internal/schedules/dispatch", dependencies=[Depends(authenticate_internal)]
    )
    async def dispatch(
        service: Annotated[RankCheckWorker, Depends(worker)],
        reports: Annotated[ReportWorker, Depends(report_worker)],
    ) -> dict[str, int]:
        count = await RankScheduleService(service.batches).dispatch()
        recovered = await service.recover()
        report_dispatched = await reports.dispatch_schedules()
        report_recovered = await reports.recover(local=False)
        return {
            "dispatched": count,
            "recovered": recovered,
            "report_dispatched": report_dispatched,
            "report_recovered": report_recovered,
        }

    return app


app = create_worker_app()
