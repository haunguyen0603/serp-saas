from app.core.config import Settings
from app.services.task_queue.base import RankCheckTaskQueue
from app.services.task_queue.local import LocalTaskQueue


def create_task_queue(settings: Settings) -> RankCheckTaskQueue:
    if settings.task_queue_provider == "local":
        return LocalTaskQueue()
    from app.services.task_queue.cloud_tasks import CloudTasksRankCheckQueue

    return CloudTasksRankCheckQueue(settings)
