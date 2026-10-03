from app.ai.provider import AIProvider, FlashcardGenerationRequest


class MockProvider(AIProvider):
    def generate_flashcards(self, request: FlashcardGenerationRequest) -> list[dict]:
        return [
            {
                "front": f"O que deve ser estudado em {request.topic}?",
                "back": "Exemplo de card gerado pelo provedor mock.",
                "difficulty": request.difficulty,
                "tags": [request.subject, request.topic],
            }
        ]
