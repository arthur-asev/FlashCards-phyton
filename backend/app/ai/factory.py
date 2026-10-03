from app.ai.mock_provider import MockProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIConfigurationError, AIProvider
from app.core.config import Settings, settings


def create_ai_provider(config: Settings = settings) -> AIProvider:
    provider_name = config.ai_provider.strip().lower()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        if not config.ai_api_key:
            raise AIConfigurationError(
                "AI_API_KEY is required when AI_PROVIDER=openai."
            )
        return OpenAIProvider(
            api_key=config.ai_api_key,
            model=config.ai_model,
            base_url=config.ai_base_url,
            timeout_seconds=config.ai_timeout_seconds,
        )
    raise AIConfigurationError("AI_PROVIDER must be either 'mock' or 'openai'.")
