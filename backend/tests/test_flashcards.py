from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def create_subject(client: TestClient, name: str = "Biologia") -> dict[str, str]:
    response = client.post("/api/v1/subjects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_topic(
    client: TestClient, subject_id: str, name: str = "Botânica"
) -> dict[str, str]:
    response = client.post(
        "/api/v1/topics",
        json={"subject_id": subject_id, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_deck(
    client: TestClient,
    subject_id: str | None = None,
    name: str = "Plantas",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/decks",
        json={"name": name, "subject_id": subject_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_card(
    client: TestClient,
    deck_id: str,
    topic_id: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "deck_id": deck_id,
        "topic_id": topic_id,
        "front": "O que é clorofila?",
        "back": "Pigmento que absorve luz.",
        "tags": ["botânica", "verde", "BOTÂNICA"],
        "difficulty": "easy",
    }
    payload.update(overrides)
    response = client.post("/api/v1/cards", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_subject_topic_and_tag_crud(client: TestClient) -> None:
    subject = create_subject(client, "  Biologia  ")
    topic = create_topic(client, subject["id"], "Ecologia")
    tag_response = client.post("/api/v1/tags", json={"name": "  revisão  "})
    assert tag_response.status_code == 201
    tag = tag_response.json()

    subjects = client.get("/api/v1/subjects?search=biolog&page=1&page_size=10")
    topics = client.get(f"/api/v1/topics?subject_id={subject['id']}")
    tags = client.get("/api/v1/tags?search=REV")
    assert subjects.json()["items"][0]["name"] == "Biologia"
    assert subjects.json()["total"] == 1
    assert topics.json()["items"][0]["id"] == topic["id"]
    assert tags.json()["items"][0]["name"] == "revisão"

    updated_subject = client.put(
        f"/api/v1/subjects/{subject['id']}",
        json={"name": "Ciências", "description": "Conteúdo escolar"},
    )
    updated_topic = client.put(
        f"/api/v1/topics/{topic['id']}",
        json={"subject_id": subject["id"], "name": "Ecologia geral"},
    )
    updated_tag = client.put(f"/api/v1/tags/{tag['id']}", json={"name": "estudo"})
    assert updated_subject.json()["name"] == "Ciências"
    assert updated_topic.json()["name"] == "Ecologia geral"
    assert updated_tag.json()["name"] == "estudo"

    assert client.get(f"/api/v1/subjects/{subject['id']}").status_code == 200
    assert client.get(f"/api/v1/topics/{topic['id']}").status_code == 200
    assert client.get(f"/api/v1/tags/{tag['id']}").status_code == 200
    assert client.delete(f"/api/v1/topics/{topic['id']}").status_code == 204
    assert client.delete(f"/api/v1/subjects/{subject['id']}").status_code == 204
    assert client.delete(f"/api/v1/tags/{tag['id']}").status_code == 204


def test_deck_crud_and_search_pagination(client: TestClient) -> None:
    subject = create_subject(client)
    first = create_deck(client, subject["id"], "Botânica básica")
    create_deck(client, subject["id"], "Zoologia")

    listed = client.get("/api/v1/decks?search=botânica&page=1&page_size=1")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == first["id"]
    assert listed.json()["page"] == 1

    updated = client.put(
        f"/api/v1/decks/{first['id']}",
        json={"name": "Botânica avançada", "subject_id": subject["id"]},
    )
    assert updated.json()["name"] == "Botânica avançada"
    assert client.get(f"/api/v1/decks/{first['id']}").status_code == 200
    assert client.delete(f"/api/v1/decks/{first['id']}").status_code == 204
    assert client.get(f"/api/v1/decks/{first['id']}").status_code == 404


def test_card_crud_tags_search_filters_and_pagination(client: TestClient) -> None:
    subject = create_subject(client)
    topic = create_topic(client, subject["id"])
    deck = create_deck(client, subject["id"])
    card = create_card(client, deck["id"], topic["id"])
    other = create_card(
        client,
        deck["id"],
        topic["id"],
        front="Qual é a função das raízes?",
        back="Absorver água e sais minerais.",
        tags=["plantas"],
    )

    assert card["tags"] == ["botânica", "verde"]
    assert other["tags"] == ["plantas"]
    filtered = client.get(
        f"/api/v1/cards?subject_id={subject['id']}&topic_id={topic['id']}&tag=VERDE&search=clorofila"
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == card["id"]

    paged = client.get(
        f"/api/v1/cards?deck_id={deck['id']}&page=2&page_size=1&sort_by=front&order=asc"
    )
    assert paged.json()["total"] == 2
    assert paged.json()["page"] == 2
    assert len(paged.json()["items"]) == 1

    updated = client.put(
        f"/api/v1/cards/{card['id']}",
        json={
            "deck_id": deck["id"],
            "topic_id": topic["id"],
            "front": "Função da clorofila",
            "back": "Absorver luz durante a fotossíntese.",
            "tags": ["fotossíntese"],
        },
    )
    assert updated.json()["front"] == "Função da clorofila"
    assert updated.json()["tags"] == ["fotossíntese"]
    assert client.get(f"/api/v1/cards/{card['id']}").status_code == 200
    assert client.delete(f"/api/v1/cards/{card['id']}").status_code == 204
    assert client.get(f"/api/v1/cards/{card['id']}").status_code == 404


def test_card_rejects_missing_references_and_cross_subject_topic(
    client: TestClient,
) -> None:
    first_subject = create_subject(client, "Biologia")
    second_subject = create_subject(client, "Química")
    topic = create_topic(client, second_subject["id"], "Reações")
    deck = create_deck(client, first_subject["id"])

    missing_deck = client.post(
        "/api/v1/cards",
        json={
            "deck_id": "00000000-0000-0000-0000-000000000000",
            "front": "Q",
            "back": "A",
        },
    )
    wrong_topic = client.post(
        "/api/v1/cards",
        json={
            "deck_id": deck["id"],
            "topic_id": topic["id"],
            "front": "Q",
            "back": "A",
        },
    )
    blank_front = client.post(
        "/api/v1/cards",
        json={"deck_id": deck["id"], "front": "  ", "back": "A"},
    )

    assert missing_deck.status_code == 404
    assert wrong_topic.status_code == 422
    assert blank_front.status_code == 422


def test_topic_uniqueness_and_referenced_taxonomy_deletion(client: TestClient) -> None:
    subject = create_subject(client)
    topic = create_topic(client, subject["id"])
    deck = create_deck(client, subject["id"])
    create_card(client, deck["id"], topic["id"])

    duplicate_topic = client.post(
        "/api/v1/topics",
        json={"subject_id": subject["id"], "name": topic["name"]},
    )
    assert duplicate_topic.status_code == 409
    assert client.delete(f"/api/v1/topics/{topic['id']}").status_code == 409
    assert client.delete(f"/api/v1/subjects/{subject['id']}").status_code == 409


def test_deleting_deck_cascades_cards_and_tag_links(client: TestClient) -> None:
    deck = create_deck(client)
    card = create_card(client, deck["id"])

    response = client.delete(f"/api/v1/decks/{deck['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/cards/{card['id']}").status_code == 404
    assert client.get("/api/v1/tags").json()["total"] == 2
