import json

import httpx
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai import provider as provider_module
from app.ai.factory import create_ai_provider
from app.ai.mock_provider import MockProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    FlashcardGenerationRequest,
    GeneratedFlashcard,
)
from app.ai.service import generate_flashcards
from app.api.v1.routes import ai as ai_routes
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
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


def make_request(quantity: int = 2) -> FlashcardGenerationRequest:
    return FlashcardGenerationRequest(
        subject="Biologia",
        topic="Fotossíntese",
        content="Clorofila absorve energia luminosa.",
        quantity=quantity,
        difficulty="medium",
        objective="Revisar conceitos centrais",
        language="pt-BR",
    )


def make_provider_response(cards: list[dict[str, object]]) -> dict[str, object]:
    return {"choices": [{"message": {"content": json.dumps({"cards": cards})}}]}


def make_provider_card(
    front: str = "Pergunta", back: str = "Resposta"
) -> dict[str, object]:
    return {"front": front, "back": back, "tags": ["biologia"]}


def test_mock_provider_generates_requested_quantity() -> None:
    request = make_request(quantity=4)

    cards = generate_flashcards(MockProvider(), request)

    assert len(cards) == request.quantity
    assert len({card.front for card in cards}) == request.quantity
    assert cards[0].source == "mock"


def test_generation_service_rejects_duplicate_cards() -> None:
    class DuplicateProvider:
        name = "test"
        model = "test-v1"

        def generate_flashcards(
            self, request: FlashcardGenerationRequest
        ) -> list[GeneratedFlashcard]:
            return [
                GeneratedFlashcard(front="Question", back="Answer"),
                GeneratedFlashcard(front=" question ", back="answer"),
            ]

    with pytest.raises(AIResponseError, match="duplicate"):
        generate_flashcards(DuplicateProvider(), make_request())


def test_generation_service_rejects_wrong_card_count() -> None:
    class ShortProvider:
        name = "test"
        model = "test-v1"

        def generate_flashcards(
            self, request: FlashcardGenerationRequest
        ) -> list[GeneratedFlashcard]:
            return [GeneratedFlashcard(front="Question", back="Answer")]

    with pytest.raises(AIResponseError, match="unexpected number"):
        generate_flashcards(ShortProvider(), make_request(quantity=2))


def test_openai_provider_parses_structured_response() -> None:
    expected_cards = [
        make_provider_card("Question 1", "Answer 1"),
        make_provider_card("Question 2", "Answer 2"),
    ]

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://ai.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-secret"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["response_format"] == {"type": "json_object"}
        prompt = json.loads(body["messages"][1]["content"])
        assert prompt["objective"] == "Revisar conceitos centrais"
        return httpx.Response(200, json=make_provider_response(expected_cards))

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = OpenAIProvider(
        api_key="test-secret",
        model="test-model",
        base_url="https://ai.example/v1/",
        client=client,
    )

    try:
        cards = provider.generate_flashcards(make_request())
    finally:
        client.close()

    assert [card.front for card in cards] == ["Question 1", "Question 2"]


def test_openai_provider_sanitizes_http_errors() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                401, json={"error": "private response body"}
            )
        )
    )
    provider = OpenAIProvider(
        "test-secret", "test-model", "https://ai.example/v1", client=client
    )

    try:
        with pytest.raises(AIProviderError, match="401") as error:
            provider.generate_flashcards(make_request())
    finally:
        client.close()

    assert "private response body" not in str(error.value)
    assert "test-secret" not in str(error.value)


def test_openai_provider_rejects_invalid_response_shape() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, json=make_provider_response([{"front": "missing back"}])
            )
        )
    )
    provider = OpenAIProvider(
        "test-secret", "test-model", "https://ai.example/v1", client=client
    )

    try:
        with pytest.raises(AIResponseError, match="invalid flashcard"):
            provider.generate_flashcards(make_request())
    finally:
        client.close()


def test_openai_provider_converts_timeout_to_provider_error() -> None:
    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    client = httpx.Client(transport=httpx.MockTransport(timeout))
    provider = OpenAIProvider(
        "test-secret", "test-model", "https://ai.example/v1", client=client
    )

    try:
        with pytest.raises(AIProviderError, match="timed out"):
            provider.generate_flashcards(make_request())
    finally:
        client.close()


def test_provider_factory_requires_openai_key() -> None:
    config = Settings(
        database_url="sqlite://",
        secret_key="test-secret",
        ai_provider="openai",
        ai_api_key=None,
    )

    with pytest.raises(AIConfigurationError, match="AI_API_KEY is required"):
        create_ai_provider(config)


def make_api_request(deck_id: str | None = None) -> dict[str, object]:
    return {
        "deck_id": deck_id,
        "subject": "Biologia",
        "topic": "Fotossíntese",
        "content": "Clorofila absorve energia luminosa.",
        "quantity": 3,
        "difficulty": "medium",
        "objective": "Revisar conceitos centrais",
        "language": "pt-BR",
    }


def test_api_generation_persists_and_lists_history(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_routes, "create_ai_provider", lambda: MockProvider())

    response = api_client.post("/api/v1/ai/generate-cards", json=make_api_request())

    assert response.status_code == 201
    generation = response.json()
    assert generation["status"] == "COMPLETED"
    assert generation["provider"] == "mock"
    assert len(generation["cards"]) == 3
    assert generation["request"]["content"] == "Clorofila absorve energia luminosa."

    detail = api_client.get(f"/api/v1/ai/generations/{generation['id']}")
    listing = api_client.get(
        "/api/v1/ai/generations?status=completed&page=1&page_size=10"
    )
    assert detail.status_code == 200
    assert detail.json()["cards"] == generation["cards"]
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == generation["id"]


def test_api_generation_requires_existing_deck(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/ai/generate-cards",
        json=make_api_request("00000000-0000-0000-0000-000000000000"),
    )

    assert response.status_code == 404
    assert api_client.get("/api/v1/ai/generations").json()["total"] == 0


def test_api_records_provider_configuration_failure(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_configuration():
        raise AIConfigurationError("missing private api key")

    monkeypatch.setattr(ai_routes, "create_ai_provider", fail_configuration)

    response = api_client.post("/api/v1/ai/generate-cards", json=make_api_request())
    listing = api_client.get("/api/v1/ai/generations?status=failed")
    generation_id = listing.json()["items"][0]["id"]
    detail = api_client.get(f"/api/v1/ai/generations/{generation_id}")

    assert response.status_code == 503
    assert "private api key" not in response.text
    assert listing.json()["total"] == 1
    assert detail.json()["error_code"] == "PROVIDER_CONFIGURATION_ERROR"


def test_api_records_invalid_provider_output(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DuplicateProvider:
        name = "test"
        model = "test-v1"

        def generate_flashcards(
            self,
            request: provider_module.FlashcardGenerationRequest,
        ) -> list[GeneratedFlashcard]:
            return [
                GeneratedFlashcard(front="Same question", back="Same answer")
                for _ in range(request.quantity)
            ]

    monkeypatch.setattr(ai_routes, "create_ai_provider", lambda: DuplicateProvider())

    response = api_client.post("/api/v1/ai/generate-cards", json=make_api_request())
    listing = api_client.get("/api/v1/ai/generations?status=failed")

    assert response.status_code == 502
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["provider"] == "test"
