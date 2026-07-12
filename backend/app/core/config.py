from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ChatCore API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chatcore"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/chatcore"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    SENTRY_DSN: Optional[str] = None

    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_PREFIX: str = "chatcore_"

    VECTOR_DB_TYPE: str = "qdrant"
    EMBEDDING_DIMENSION: int = 1536
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 75
    TOP_K_RETRIEVAL: int = 5

    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_SITES_PER_TENANT: int = 10
    MAX_CHUNKS_PER_SITE: int = 100000

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://app.chatcore.dev"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
