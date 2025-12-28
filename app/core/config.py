"""Application configuration settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "MentraFlow API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/mentraflow"

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"  # For LLM/chat operations
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # For embeddings (1536 dimensions)

    # Qdrant settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_PREFIX: str = "mentraflow"

    # Database auto-creation (development only)
    AUTO_CREATE_TABLES: bool = False
    DROP_AND_RECREATE_TABLES: bool = False  # WARNING: Drops all tables before creating (development only!)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()

