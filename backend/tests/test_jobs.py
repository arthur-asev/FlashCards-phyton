from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.provider import AIProviderError
from app.api.v1.routes.jobs import get_redis_client
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import BackgroundJob
from app.workers import worker


class FakeRedis:
    def __init__(self) -> None:
        self.values: list[str] = []

    def lpush(self, _queue: str, *values: str) -> int:
        for value in values:
            self.values.insert(0, value)
        return len(self.values)

    def brpop(self, queue: str, timeout: int = 0) -> tuple[str, str] | None:
        if not self.values:
            return None
        return queue, self.values.pop()


@pytest.fixture
def job_context() -> Generator[
    tuple[TestClient, sessionmaker[Session], FakeRedis], None, None
]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    redis = FakeRedis()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: redis
    with TestClient(app) as client:
        yield client, session_factory, redis
    app.dependency_overrides.clear()
    engine.dispose()


def make_payload() -> dict[str, object]:
    return {
        "subject": "Biologia",
        "topic": "Fotossíntese",
        "content": "A clorofila absorve energia luminosa.",
        "quantity": 2,
        "difficulty": "medium",
        "objective": "Revisar conceitos",
        "language": "pt-BR",
    }


def create_job(
    session_factory: sessionmaker[Session],
    *,
    status: str = "PENDING",
    attempts: int = 0,
    max_attempts: int = 3,
    started_at: datetime | None = None,
) -> UUID:
    with session_factory() as session:
        job = BackgroundJob(
            job_type="ai_generation",
            status=status,
            payload=make_payload(),
            attempts=attempts,
            max_attempts=max_attempts,
            started_at=started_at,
        )
        session.add(job)
        session.commit()
        return job.id


def read_job(session_factory: sessionmaker[Session], job_id: UUID) -> BackgroundJob:
    with session_factory() as session:
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        session.expunge(job)
        return job


def test_enqueue_endpoint_creates_job_and_worker_completes_it(
    job_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory, redis = job_context
    monkeypatch.setattr(
        worker,
        "run_ai_generation",
        lambda _payload: {
            "provider": "mock",
            "model": "mock-v1",
            "cards": [{"front": "Q", "back": "A"}],
        },
    )

    response = client.post("/api/v1/jobs/ai-generations", json=make_payload())

    assert response.status_code == 202
    job_data = response.json()
    assert job_data["status"] == "PENDING"
    assert redis.values == [job_data["id"]]
    job_id = UUID(job_data["id"])

    assert worker.run_once(session_factory, redis, timeout=0) is True
    completed = client.get(f"/api/v1/jobs/{job_id}").json()
    assert completed["status"] == "COMPLETED"
    assert completed["attempts"] == 1
    assert completed["result"]["cards"][0]["front"] == "Q"


def test_worker_retries_transient_provider_failure(
    job_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, session_factory, redis = job_context
    job_id = create_job(session_factory, max_attempts=2)
    calls = 0

    def fail_once(_payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AIProviderError("temporary provider failure")
        return {"provider": "mock", "model": "mock-v1", "cards": []}

    monkeypatch.setattr(worker, "run_ai_generation", fail_once)

    assert worker.process_job(job_id, session_factory, redis) is True
    retrying = read_job(session_factory, job_id)
    assert retrying.status == "PENDING"
    assert retrying.attempts == 1
    assert retrying.error_code == "PROVIDER_REQUEST_FAILED"
    assert redis.values == [str(job_id)]

    assert worker.run_once(session_factory, redis, timeout=0) is True
    completed = read_job(session_factory, job_id)
    assert completed.status == "COMPLETED"
    assert completed.attempts == 2


def test_worker_marks_job_failed_after_retry_limit(
    job_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, session_factory, redis = job_context
    job_id = create_job(session_factory, max_attempts=2)
    monkeypatch.setattr(
        worker,
        "run_ai_generation",
        lambda _payload: (_ for _ in ()).throw(AIProviderError("offline")),
    )

    worker.process_job(job_id, session_factory, redis)
    worker.process_job(job_id, session_factory, redis)

    failed = read_job(session_factory, job_id)
    assert failed.status == "FAILED"
    assert failed.attempts == 2
    assert failed.error_code == "PROVIDER_REQUEST_FAILED"
    assert failed.error_message == "AI provider request failed."
    assert redis.values == [str(job_id)]


def test_manual_retry_adds_one_attempt_and_requeues(job_context) -> None:
    client, session_factory, redis = job_context
    job_id = create_job(session_factory, status="FAILED", attempts=3, max_attempts=3)

    response = client.post(f"/api/v1/jobs/{job_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    assert response.json()["attempts"] == 3
    assert response.json()["max_attempts"] == 4
    assert redis.values == [str(job_id)]


def test_manual_retry_rejects_non_failed_job(job_context) -> None:
    client, session_factory, _redis = job_context
    job_id = create_job(session_factory)

    response = client.post(f"/api/v1/jobs/{job_id}/retry")

    assert response.status_code == 409


def test_enqueue_rejects_missing_deck(job_context) -> None:
    client, _session_factory, redis = job_context
    payload = {**make_payload(), "deck_id": "00000000-0000-0000-0000-000000000000"}

    response = client.post("/api/v1/jobs/ai-generations", json=payload)

    assert response.status_code == 404
    assert redis.values == []


def test_worker_recovers_stale_processing_jobs(job_context) -> None:
    _client, session_factory, redis = job_context
    now = datetime.now(timezone.utc)
    retryable_id = create_job(
        session_factory,
        status="PROCESSING",
        attempts=1,
        max_attempts=3,
        started_at=now - timedelta(minutes=10),
    )
    exhausted_id = create_job(
        session_factory,
        status="PROCESSING",
        attempts=3,
        max_attempts=3,
        started_at=now - timedelta(minutes=10),
    )

    with session_factory() as session:
        recovered_count = worker.recover_stale_jobs(session, redis, now=now)

    assert recovered_count == 1
    assert read_job(session_factory, retryable_id).status == "PENDING"
    exhausted = read_job(session_factory, exhausted_id)
    assert exhausted.status == "FAILED"
    assert exhausted.error_code == "WORKER_INTERRUPTED"
    assert redis.values == [str(retryable_id)]


def test_duplicate_queue_delivery_does_not_run_completed_job_twice(
    job_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, session_factory, redis = job_context
    job_id = create_job(session_factory)
    calls = 0

    def complete(_payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"provider": "mock", "model": "mock-v1", "cards": []}

    monkeypatch.setattr(worker, "run_ai_generation", complete)

    assert worker.process_job(job_id, session_factory, redis) is True
    assert worker.process_job(job_id, session_factory, redis) is False
    assert calls == 1
    assert read_job(session_factory, job_id).attempts == 1
