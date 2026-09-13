"""Zero-credit batch/worker smoke with an explicit fake provider."""

import asyncio
from uuid import UUID

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.rank_job import RankCheckJob
from app.services.rank_batches import RankBatchService
from app.services.rank_worker import RankCheckWorker
from app.services.serp.factory import get_provider_router
from app.services.task_queue.local import LocalTaskQueue
from scripts.smoke_rankings import register


async def verify(project: UUID, user: UUID) -> None:
    settings = get_settings().model_copy(
        update={
            "serp_provider": "fake",
            "serp_enabled_providers": "fake",
            "serp_provider_strategy": "fixed",
            "serp_fixed_provider": "fake",
            "task_queue_provider": "local",
        }
    )
    engine = create_engine(settings)
    try:
        factory = create_session_factory(engine)
        batches = RankBatchService(factory, settings, LocalTaskQueue())
        worker = RankCheckWorker(batches, get_provider_router(settings, factory))
        batch = await batches.create(project, user)
        async with factory() as session:
            jobs = list(
                await session.scalars(
                    select(RankCheckJob.id).where(
                        RankCheckJob.batch_id == batch.batch_id
                    )
                )
            )
        for job in jobs:
            # The Compose local worker may already hold this Job's lease.
            for _ in range(300):
                if await worker.execute(job):
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("Local Job did not reach a terminal state")
            assert await worker.execute(job)
        detail = await batches.detail(project, user, batch.batch_id)
        assert detail.status == "completed" and detail.succeeded_keyword_count == 2
        print(
            "PASS: local async batch, two jobs, duplicate delivery; "
            "progress 100%, zero external credits"
        )
    finally:
        await engine.dispose()


def main() -> None:
    with httpx.Client(
        base_url=f"http://127.0.0.1:{get_settings().backend_port}", timeout=20
    ) as client:
        headers, user = register(client)
        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "M5 smoke",
                "country_code": "VN",
                "language_code": "vi",
                "device": "desktop",
                "keywords": ["async one", "async two"],
            },
        )
        assert response.status_code == 201
        asyncio.run(verify(UUID(response.json()["project"]["id"]), user))


if __name__ == "__main__":
    main()
