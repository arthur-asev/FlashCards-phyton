import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.ai.factory import create_ai_provider
from app.ai.provider import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    FlashcardGenerationRequest,
)
from app.ai.service import generate_flashcards
from app.db.session import SessionLocal
from app.jobs.queue import JOB_QUEUE, dequeue_job, enqueue_job, redis_client
from app.models import BackgroundJob

logger = logging.getLogger(__name__)
JOB_TYPE_AI_GENERATION = "ai_generation"
STALE_JOB_AFTER = timedelta(minutes=5)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def set_failed(job: BackgroundJob, error_code: str, message: str) -> None:
    job.status = "FAILED"
    job.error_code = error_code
    job.error_message = message
    job.completed_at = utc_now()


def run_ai_generation(payload: dict[str, object]) -> dict[str, object]:
    request = FlashcardGenerationRequest.model_validate(payload)
    provider = create_ai_provider()
    cards = generate_flashcards(provider, request)
    return {
        "provider": provider.name,
        "model": provider.model,
        "cards": [card.model_dump(mode="json") for card in cards],
    }


def process_job(
    job_id: UUID,
    session_factory: Callable[[], Session] = SessionLocal,
    client: Redis = redis_client,
) -> bool:
    with session_factory() as db:
        claim = db.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id, BackgroundJob.status == "PENDING")
            .values(
                status="PROCESSING",
                attempts=BackgroundJob.attempts + 1,
                started_at=utc_now(),
                error_code=None,
                error_message=None,
            )
        )
        db.commit()
        if claim.rowcount != 1:
            return False

        job = db.get(BackgroundJob, job_id)
        if job is None:
            return False

        try:
            if job.job_type != JOB_TYPE_AI_GENERATION:
                set_failed(job, "UNKNOWN_JOB_TYPE", "Unsupported background job type.")
                db.commit()
                return True
            result = run_ai_generation(job.payload)
        except AIProviderError:
            if job.attempts < job.max_attempts:
                job.status = "PENDING"
                job.error_code = "PROVIDER_REQUEST_FAILED"
                job.error_message = "AI provider request failed; retry scheduled."
                db.commit()
                try:
                    enqueue_job(job.id, client)
                except RedisError:
                    set_failed(job, "QUEUE_UNAVAILABLE", "Unable to schedule a retry.")
                    db.commit()
            else:
                set_failed(
                    job, "PROVIDER_REQUEST_FAILED", "AI provider request failed."
                )
                db.commit()
            return True
        except (AIConfigurationError, AIResponseError, ValidationError):
            set_failed(
                job,
                "INVALID_JOB_OR_PROVIDER_RESPONSE",
                "Job input or provider response is invalid.",
            )
            db.commit()
            return True
        except Exception as exc:
            logger.error(
                "background_job_failed job_id=%s error_type=%s",
                job_id,
                type(exc).__name__,
            )
            set_failed(
                job, "UNEXPECTED_JOB_ERROR", "Background job failed unexpectedly."
            )
            db.commit()
            return True

        job.result = result
        job.status = "COMPLETED"
        job.error_code = None
        job.error_message = None
        job.completed_at = utc_now()
        db.commit()
        return True


def recover_stale_jobs(
    db: Session,
    client: Redis = redis_client,
    now: datetime | None = None,
) -> int:
    recovery_time = now or utc_now()
    stale_before = recovery_time - STALE_JOB_AFTER
    stale_jobs = db.scalars(
        select(BackgroundJob).where(
            BackgroundJob.status == "PROCESSING",
            BackgroundJob.started_at < stale_before,
        )
    ).all()
    for job in stale_jobs:
        if job.attempts >= job.max_attempts:
            set_failed(
                job, "WORKER_INTERRUPTED", "Worker stopped before completing the job."
            )
        else:
            job.status = "PENDING"
            job.error_code = "WORKER_INTERRUPTED"
            job.error_message = "Job was requeued after an interrupted worker."
    db.commit()

    pending_ids = db.scalars(
        select(BackgroundJob.id).where(BackgroundJob.status == "PENDING")
    ).all()
    if pending_ids:
        client.lpush(JOB_QUEUE, *(str(job_id) for job_id in pending_ids))
    return len(pending_ids)


def run_once(
    session_factory: Callable[[], Session] = SessionLocal,
    client: Redis = redis_client,
    timeout: int = 5,
) -> bool:
    job_id = dequeue_job(client, timeout=timeout)
    if job_id is None:
        return False
    return process_job(job_id, session_factory, client)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        requeued_count = recover_stale_jobs(db)
    logger.info("background_worker_started requeued=%s", requeued_count)
    while True:
        try:
            run_once()
        except RedisError as exc:
            logger.error(
                "background_queue_unavailable error_type=%s", type(exc).__name__
            )


if __name__ == "__main__":
    main()
