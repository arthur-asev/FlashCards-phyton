from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.ai.provider import FlashcardGenerationRequest
from app.db.session import get_db
from app.jobs.queue import enqueue_job, get_redis_client
from app.models import BackgroundJob, Deck

router = APIRouter()


def serialize_job(job: BackgroundJob) -> dict[str, object]:
    return {
        "id": str(job.id),
        "type": job.job_type,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "result": job.result,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.post("/ai-generations", status_code=status.HTTP_202_ACCEPTED)
def enqueue_ai_generation(
    request: FlashcardGenerationRequest,
    db: Session = Depends(get_db),
    client: Redis = Depends(get_redis_client),
) -> dict[str, object]:
    if request.deck_id is not None and db.get(Deck, request.deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck not found.")

    job = BackgroundJob(
        job_type="ai_generation",
        payload=request.model_dump(mode="json"),
        max_attempts=3,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        enqueue_job(job.id, client)
    except RedisError as exc:
        job.status = "FAILED"
        job.error_code = "QUEUE_UNAVAILABLE"
        job.error_message = "Unable to enqueue background job."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Background job queue is unavailable.",
        ) from exc
    return serialize_job(job)


@router.get("/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialize_job(job)


@router.post("/{job_id}/retry")
def retry_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    client: Redis = Depends(get_redis_client),
) -> dict[str, object]:
    job = db.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "FAILED":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried.")

    job.max_attempts += 1
    job.status = "PENDING"
    job.error_code = None
    job.error_message = None
    job.result = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    try:
        enqueue_job(job.id, client)
    except RedisError as exc:
        job.status = "FAILED"
        job.error_code = "QUEUE_UNAVAILABLE"
        job.error_message = "Unable to enqueue background job."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Background job queue is unavailable.",
        ) from exc
    db.refresh(job)
    return serialize_job(job)
