from uuid import UUID

from redis import Redis

from app.core.config import settings

JOB_QUEUE = "flashcard:jobs:pending"
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis_client() -> Redis:
    return redis_client


def enqueue_job(job_id: UUID, client: Redis = redis_client) -> None:
    client.lpush(JOB_QUEUE, str(job_id))


def dequeue_job(client: Redis = redis_client, timeout: int = 5) -> UUID | None:
    result = client.brpop(JOB_QUEUE, timeout=timeout)
    if result is None:
        return None
    return UUID(result[1])
