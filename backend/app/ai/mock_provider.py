from app.ai.provider import FlashcardGenerationRequest, GeneratedFlashcard


class MockProvider:
    name = "mock"
    model = "mock-v1"

    def generate_flashcards(
        self,
        request: FlashcardGenerationRequest,
    ) -> list[GeneratedFlashcard]:
        return [
            GeneratedFlashcard(
                front=f"Pergunta de demonstração {index + 1} sobre {request.topic}",
                back=f"Conteúdo de demonstração: {request.content[:160]}",
                difficulty=request.difficulty,
                tags=[request.subject, request.topic],
                source="mock",
            )
            for index in range(request.quantity)
        ]
