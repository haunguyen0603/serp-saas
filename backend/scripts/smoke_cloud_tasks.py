"""Opt-in single-task delivery for an existing dedicated smoke job."""

import asyncio
import os
from uuid import UUID

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.models.rank_job import RankCheckJob
from app.services.task_queue.cloud_tasks import CloudTasksRankCheckQueue


async def main() -> None:
    if os.getenv("RUN_REAL_CLOUD_TASKS_SMOKE") != "true":
        print("SKIPPED — RUN_REAL_CLOUD_TASKS_SMOKE is not true")
        return
    settings = get_settings()
    job_id = os.getenv("CLOUD_TASKS_SMOKE_JOB_ID")
    if settings.task_queue_provider != "cloud_tasks" or not job_id:
        print(
            "SKIPPED — real GCP Cloud Tasks environment "
            "or dedicated smoke Job not configured"
        )
        return
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        job_uuid = UUID(job_id)
        async with factory() as session:
            job = await session.get(RankCheckJob, job_uuid)
            if not job or job.status != "pending":
                raise SystemExit(
                    "Smoke requires a dedicated pending Job in this database"
                )
        await CloudTasksRankCheckQueue(settings).enqueue_rank_check_job(job_uuid)
        for _ in range(30):
            async with factory() as session:
                job = await session.get(RankCheckJob, job_uuid)
                if job and job.status in {"succeeded", "failed", "cancelled"}:
                    assert job.status == "succeeded", "Smoke Job did not succeed"
                    print(
                        "PASS: one authenticated Cloud Tasks delivery reached succeeded"
                    )
                    return
            await asyncio.sleep(2)
        raise SystemExit("Smoke delivery did not complete within 60 seconds")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
