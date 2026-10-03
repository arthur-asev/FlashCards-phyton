from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Review


@pytest.fixture
def review_context() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def create_card(client: TestClient, deck_name: str = "Biologia") -> dict[str, object]:
    deck_response = client.post("/api/v1/decks", json={"name": deck_name})
    assert deck_response.status_code == 201
    card_response = client.post(
        "/api/v1/cards",
        json={
            "deck_id": deck_response.json()["id"],
            "front": f"Pergunta de {deck_name}",
            "back": "Resposta",
        },
    )
    assert card_response.status_code == 201
    return card_response.json()


def test_review_submission_schedules_and_removes_future_card_from_due(
    review_context,
) -> None:
    client, _session_factory = review_context
    card = create_card(client)

    response = client.post(
        f"/api/v1/cards/{card['id']}/review",
        json={"rating": 4},
    )

    assert response.status_code == 201
    review = response.json()
    assert review["card_id"] == card["id"]
    assert review["interval"] == 1
    assert review["repetitions"] == 1
    assert review["card"]["front"] == card["front"]

    due = client.get("/api/v1/reviews/due")
    assert due.status_code == 200
    assert due.json()["total"] == 0


def test_due_cards_include_unreviewed_cards_and_support_filters(review_context) -> None:
    client, _session_factory = review_context
    first = create_card(client, "Biologia")
    create_card(client, "Química")

    due = client.get("/api/v1/reviews/due?page=1&page_size=1")
    filtered = client.get(f"/api/v1/reviews/due?deck_id={first['deck_id']}")

    assert due.json()["total"] == 2
    assert len(due.json()["items"]) == 1
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == first["id"]
    assert filtered.json()["items"][0]["next_review_at"] is None


def test_review_history_is_persisted_and_paginated(review_context) -> None:
    client, session_factory = review_context
    card = create_card(client)

    first = client.post(f"/api/v1/cards/{card['id']}/review", json={"rating": 5})
    with session_factory() as session:
        previous_review = session.get(Review, UUID(first.json()["id"]))
        assert previous_review is not None
        previous_review.next_review_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.commit()

    second = client.post(f"/api/v1/cards/{card['id']}/review", json={"rating": 5})
    history = client.get(f"/api/v1/reviews/history?card_id={card['id']}&page_size=1")

    assert second.status_code == 201
    assert second.json()["interval"] == 6
    assert history.json()["total"] == 2
    assert len(history.json()["items"]) == 1
    assert history.json()["items"][0]["id"] == second.json()["id"]
    assert history.json()["items"][0]["card"]["id"] == card["id"]


def test_review_stats_count_pending_due_and_review_history(review_context) -> None:
    client, _session_factory = review_context
    card = create_card(client)
    create_card(client, "Química")
    client.post(f"/api/v1/cards/{card['id']}/review", json={"rating": 4})

    stats = client.get("/api/v1/reviews/stats")

    assert stats.status_code == 200
    assert stats.json() == {
        "total_cards": 2,
        "reviewed_cards": 1,
        "pending_cards": 1,
        "due_cards": 1,
        "total_reviews": 1,
    }


def test_review_rejects_invalid_rating_and_missing_card(review_context) -> None:
    client, _session_factory = review_context
    card = create_card(client)

    invalid_rating = client.post(
        f"/api/v1/cards/{card['id']}/review", json={"rating": 6}
    )
    missing_card = client.post(
        "/api/v1/cards/00000000-0000-0000-0000-000000000000/review",
        json={"rating": 4},
    )

    assert invalid_rating.status_code == 422
    assert missing_card.status_code == 404
