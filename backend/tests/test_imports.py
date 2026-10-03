from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import files as file_routes
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def import_context(tmp_path, monkeypatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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
    monkeypatch.setattr(file_routes, "STORAGE_ROOT", tmp_path)
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def test_confirmed_import_creates_cards_tags_topic_and_import_history(import_context) -> None:
    client, _session_factory = import_context
    subject = client.post("/api/v1/subjects", json={"name": "Biologia"}).json()
    deck = client.post(
        "/api/v1/decks",
        json={"name": "Botânica", "subject_id": subject["id"]},
    ).json()
    content = "Pergunta,Resposta,Assunto,Tags\nO que é clorofila?,Pigmento verde,Botânica,planta; luz\n".encode("utf-8")
    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("cards.csv", content, "text/csv")},
    )
    file_id = upload.json()["id"]

    response = client.post(
        "/api/v1/imports",
        json={
            "file_id": file_id,
            "deck_id": deck["id"],
            "mapping": {
                "front": "Pergunta",
                "back": "Resposta",
                "topic": "Assunto",
                "tags": "Tags",
            },
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["processed_rows"] == 1
    cards = client.get(f"/api/v1/cards?deck_id={deck['id']}").json()
    assert cards["total"] == 1
    assert cards["items"][0]["front"] == "O que é clorofila?"
    assert cards["items"][0]["tags"] == ["luz", "planta"]
    assert cards["items"][0]["topic_id"]


def test_import_requires_validation_and_existing_deck(import_context) -> None:
    client, _session_factory = import_context
    uploaded = client.post(
        "/api/v1/files/upload",
        files={"file": ("cards.csv", b"front,back\nQuestion,\n", "text/csv")},
    ).json()
    deck = client.post("/api/v1/decks", json={"name": "Deck"}).json()

    invalid = client.post(
        "/api/v1/imports",
        json={
            "file_id": uploaded["id"],
            "deck_id": deck["id"],
            "mapping": {"front": "front", "back": "back"},
        },
    )
    missing_deck = client.post(
        "/api/v1/imports",
        json={
            "file_id": uploaded["id"],
            "deck_id": "00000000-0000-0000-0000-000000000000",
            "mapping": {"front": "front", "back": "back"},
        },
    )

    assert invalid.status_code == 422
    assert missing_deck.status_code == 404
    assert client.get(f"/api/v1/cards?deck_id={deck['id']}").json()["total"] == 0