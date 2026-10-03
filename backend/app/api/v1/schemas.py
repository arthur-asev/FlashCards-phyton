from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubjectWrite(StrictInput):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be empty.")
        return normalized


class TopicWrite(SubjectWrite):
    subject_id: UUID
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class TagWrite(StrictInput):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be empty.")
        return normalized


class DeckWrite(StrictInput):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    subject_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be empty.")
        return normalized


class CardWrite(StrictInput):
    deck_id: UUID
    topic_id: UUID | None = None
    front: str = Field(min_length=1, max_length=10000)
    back: str = Field(min_length=1, max_length=10000)
    explanation: str | None = Field(default=None, max_length=10000)
    example: str | None = Field(default=None, max_length=10000)
    difficulty: str | None = Field(default=None, max_length=30)
    source: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=100)

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
            key = tag.casefold()
            if key not in seen:
                seen.add(key)
                normalized_tags.append(tag)
        return normalized_tags
