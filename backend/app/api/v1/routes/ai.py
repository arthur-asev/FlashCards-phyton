from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.factory import create_ai_provider
from app.ai.provider import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    FlashcardGenerationRequest,
)
from app.ai.service import generate_flashcards
from app.api.v1.routes.pagination import paginate
from app.db.session import get_db
from app.models import AIGeneration, Deck
from app.core.config import settings

router = APIRouter()


def serialize_generation(
    generation: AIGeneration,
    include_result: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(generation.id),
        "deck_id": str(generation.deck_id) if generation.deck_id else None,
        "provider": generation.provider,
        "model": generation.model,
        "status": generation.status,
        "created_at": generation.created_at,
        "card_count": len(generation.generation_metadata.get("cards", [])),
    }
    if include_result:
        result["request"] = generation.generation_metadata.get("request")
        result["cards"] = generation.generation_metadata.get("cards", [])
        result["error_code"] = generation.generation_metadata.get("error_code")
    return result


def mark_generation_failed(
    db: Session,
    generation: AIGeneration,
    error_code: str,
) -> None:
    generation.status = "FAILED"
    generation.generation_metadata = {
        **generation.generation_metadata,
        "error_code": error_code,
    }
    db.commit()


@router.post("/generate-cards", status_code=status.HTTP_201_CREATED)
def generate_cards(
    request: FlashcardGenerationRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if request.deck_id is not None and db.get(Deck, request.deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck not found.")

    generation = AIGeneration(
        deck_id=request.deck_id,
        provider=settings.ai_provider,
        model=settings.ai_model if settings.ai_provider == "openai" else None,
        status="PROCESSING",
        generation_metadata={
            "request": request.model_dump(mode="json"),
            "cards": [],
        },
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    try:
        provider = create_ai_provider()
        generation.provider = provider.name
        generation.model = provider.model
        db.commit()
        cards = generate_flashcards(provider, request)
    except AIConfigurationError as exc:
        mark_generation_failed(db, generation, "PROVIDER_CONFIGURATION_ERROR")
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured.",
        ) from exc
    except AIProviderError as exc:
        mark_generation_failed(db, generation, "PROVIDER_REQUEST_FAILED")
        raise HTTPException(
            status_code=502,
            detail="AI provider request failed.",
        ) from exc
    except AIResponseError as exc:
        mark_generation_failed(db, generation, "INVALID_PROVIDER_RESPONSE")
        raise HTTPException(
            status_code=502,
            detail="AI provider returned an invalid response.",
        ) from exc

    generation.provider = provider.name
    generation.model = provider.model
    generation.status = "COMPLETED"
    generation.generation_metadata = {
        "request": request.model_dump(mode="json"),
        "cards": [card.model_dump(mode="json") for card in cards],
    }
    db.commit()
    db.refresh(generation)
    return serialize_generation(generation, include_result=True)


@router.get("/generations")
def list_generations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    generation_status: str | None = Query(default=None, alias="status"),
    deck_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(AIGeneration).order_by(
        AIGeneration.created_at.desc(), AIGeneration.id
    )
    if generation_status:
        query = query.where(AIGeneration.status == generation_status.upper())
    if deck_id is not None:
        query = query.where(AIGeneration.deck_id == deck_id)
    return paginate(
        db,
        query,
        page,
        page_size,
        lambda generation: serialize_generation(generation),
    )


@router.get("/generations/{generation_id}")
def get_generation(
    generation_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    generation = db.get(AIGeneration, generation_id)
    if generation is None:
        raise HTTPException(status_code=404, detail="Generation not found.")
    return serialize_generation(generation, include_result=True)
