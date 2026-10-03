from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router
from app.core.config import settings
from app.db.session import database_engine

redis_client = Redis.from_url(settings.redis_url)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Platform for spreadsheet conversion and flashcard management.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


def check_dependencies() -> None:
    with database_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    redis_client.ping()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    try:
        check_dependencies()
    except (SQLAlchemyError, RedisError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Application dependencies are not ready",
        ) from exc
    return {"status": "ready"}
