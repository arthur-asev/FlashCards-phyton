from dataclasses import dataclass


@dataclass
class FlashcardGenerationRequest:
    subject: str
    topic: str
    content: str
    quantity: int = 10
    difficulty: str = "medium"
    language: str = "pt-BR"


class AIProvider:
    def generate_flashcards(self, request: FlashcardGenerationRequest) -> list[dict]:
        raise NotImplementedError
