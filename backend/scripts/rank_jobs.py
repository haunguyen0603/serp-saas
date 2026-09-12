"""Local durable worker and explicit recovery, using the same application services."""

import argparse
import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine, create_session_factory
from app.services.rank_batches import RankBatchService
from app.services.rank_schedules import RankScheduleService
from app.services.rank_worker import RankCheckWorker
from app.services.serp.factory import get_provider_router
from app.services.task_queue import create_task_queue


async def run(loop: bool) -> None:
    settings = get_settings()
    if loop and (
        settings.task_queue_provider != "local" or settings.app_env == "production"
    ):
        raise SystemExit("Local worker loop requires a non-production local queue")
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    worker = RankCheckWorker(
        RankBatchService(factory, settings, create_task_queue(settings)),
        get_provider_router(settings, factory),
    )
    try:
        while True:
            await RankScheduleService(worker.batches).dispatch()
            await worker.recover(local=settings.task_queue_provider == "local")
            if not loop:
                break
            await asyncio.sleep(2)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    configure_logging()
    asyncio.run(run(parser.parse_args().loop))
