from collections.abc import Sequence

from pydantic import ValidationError

from app.ai.provider import (
    AIProvider,
    AIResponseError,
    FlashcardGenerationRequest,
    GeneratedFlashcard,
)


def generate_flashcards(
    provider: AIProvider,
    request: FlashcardGenerationRequest,
) -> list[GeneratedFlashcard]:
    try:
        provider_cards: Sequence[GeneratedFlashcard] = provider.generate_flashcards(
            request
        )
        cards = [
            card
            if isinstance(card, GeneratedFlashcard)
            else GeneratedFlashcard.model_validate(card)
            for card in provider_cards
        ]
    except ValidationError as exc:
        raise AIResponseError(
            "AI provider returned an invalid flashcard response."
        ) from exc

    if len(cards) != request.quantity:
        raise AIResponseError(
            "AI provider returned an unexpected number of flashcards."
        )

    seen_cards: set[tuple[str, str]] = set()
    for card in cards:
        key = (card.front.casefold(), card.back.casefold())
        if key in seen_cards:
            raise AIResponseError("AI provider returned duplicate flashcards.")
        seen_cards.add(key)
    return cards
