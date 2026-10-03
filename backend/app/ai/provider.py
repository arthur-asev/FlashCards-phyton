from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlashcardGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=20000)
    quantity: int = Field(default=10, ge=1, le=20)
    difficulty: str = Field(default="medium", min_length=1, max_length=30)
    objective: str = Field(default="study", min_length=1, max_length=300)
    language: str = Field(default="pt-BR", min_length=2, max_length=30)
    deck_id: UUID | None = None

    @field_validator(
        "subject", "topic", "content", "difficulty", "objective", "language"
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized


class GeneratedFlashcard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: str = Field(min_length=1, max_length=10000)
    back: str = Field(min_length=1, max_length=10000)
    explanation: str | None = Field(default=None, max_length=10000)
    example: str | None = Field(default=None, max_length=10000)
    difficulty: str | None = Field(default=None, max_length=30)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str | None = Field(default=None, max_length=500)

    @field_validator("front", "back")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Card text must not be empty.")
        return normalized

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized_tags: list[str] = []
        seen: set[str] = set()
        for value in values:
            tag = value.strip()
            if not tag:
                continue
            if len(tag) > 80:
                raise ValueError("Tag names must not exceed 80 characters.")
            if tag.casefold() not in seen:
                seen.add(tag.casefold())
                normalized_tags.append(tag)
        return normalized_tags


class FlashcardGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[GeneratedFlashcard] = Field(min_length=1, max_length=20)


class AIError(Exception):
    """Base exception for provider and response failures."""


class AIConfigurationError(AIError):
    """Raised when the selected provider is not configured."""


class AIProviderError(AIError):
    """Raised when the external AI provider cannot complete a request."""


class AIResponseError(AIError):
    """Raised when provider output cannot be validated as flashcards."""


class AIProvider(Protocol):
    name: str
    model: str

    def generate_flashcards(
        self,
        request: FlashcardGenerationRequest,
    ) -> list[GeneratedFlashcard]: ...
