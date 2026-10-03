from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Flashcard Platform"
    app_env: str = "development"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    secret_key: str
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    max_upload_size_mb: int = 25
    ai_provider: str = "mock"
    ai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
