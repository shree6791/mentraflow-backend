"""Application configuration settings.

HOW IT WORKS:
============
1. All values are read from .env file (if it exists)
2. If a value is missing in .env, the default below is used
3. Defaults are ONLY fallbacks - they should NOT be used in production
4. Create a .env file (copy from env.example) and set your actual values there

REQUIRED SETTINGS (must be in .env):
- DATABASE_URL
- OPENAI_API_KEY
- QDRANT_URL
- QDRANT_API_KEY

OPTIONAL SETTINGS (have sensible defaults):
- HOST, PORT, DEBUG, etc.
"""
import json
import logging
from typing import Any

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def strip_comment(value: Any) -> str:
    """Strip inline comments from env value (everything after #)."""
    if not isinstance(value, str):
        return str(value)
    if "#" in value:
        value = value.split("#")[0]
    return value.strip()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    ⚠️  IMPORTANT: Values come from .env file, NOT from defaults below!
    Defaults are only fallbacks for missing values.
    """

    # ============================================================================
    # Application Metadata
    # ============================================================================
    PROJECT_NAME: str = "MentraFlow API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # ============================================================================
    # Server Configuration
    # ============================================================================
    HOST: str = Field(default="0.0.0.0", description="Server host (127.0.0.1 for local-only, 0.0.0.0 for all)")
    PORT: int = Field(default=8000, description="Server port")

    # ============================================================================
    # Database Configuration (REQUIRED in .env)
    # ============================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/mentraflow",
        description="PostgreSQL connection URL. REQUIRED: Set this in .env file!",
    )

    # ============================================================================
    # CORS Configuration
    # ============================================================================
    BACKEND_CORS_ORIGINS_STR: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        validation_alias="BACKEND_CORS_ORIGINS",
        description="CORS origins as comma-separated string",
    )

    @computed_field
    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from comma-separated string or JSON array."""
        v = self.BACKEND_CORS_ORIGINS_STR.strip()
        if not v:
            return []

        # Try JSON array first
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Otherwise, treat as comma-separated string
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ============================================================================
    # OpenAI Configuration (REQUIRED in .env)
    # ============================================================================
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key. REQUIRED: Set this in .env file!")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model for LLM/chat operations")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="OpenAI model for embeddings (1536 dimensions)"
    )

    # ============================================================================
    # Qdrant Configuration (REQUIRED in .env)
    # ============================================================================
    QDRANT_URL: str = Field(
        default="http://localhost:6333", description="Qdrant server URL. REQUIRED: Set your cloud URL in .env!"
    )
    QDRANT_API_KEY: str = Field(default="", description="Qdrant API key. REQUIRED: Set this in .env file!")
    QDRANT_COLLECTION_PREFIX: str = Field(
        default="mentraflow", description="Prefix for Qdrant collection names"
    )

    # ============================================================================
    # Development & Debug Settings
    # ============================================================================
    AUTO_CREATE_TABLES: bool = Field(
        default=False, description="Auto-create tables on startup (dev/testing only, use Alembic in production)"
    )
    DROP_AND_RECREATE_TABLES: bool = Field(
        default=False, description="⚠️  DANGEROUS: Drop all tables and recreate (DELETES ALL DATA! Dev only!)"
    )
    DROP_AND_RECREATE_COLLECTIONS: bool = Field(
        default=False, description="⚠️  DANGEROUS: Drop all Qdrant collections and recreate (DELETES ALL VECTOR DATA! Dev only!)"
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode (verbose logging, FastAPI debug features)")

    # ============================================================================
    # Pydantic Configuration
    # ============================================================================
    model_config = SettingsConfigDict(
        env_file=".env",  # Read from .env file first
        case_sensitive=True,
    )

    # ============================================================================
    # Validators (applied to all string fields to strip comments)
    # ============================================================================
    @field_validator(
        "PROJECT_NAME",
        "VERSION",
        "API_V1_STR",
        "HOST",
        "DATABASE_URL",
        "BACKEND_CORS_ORIGINS_STR",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "QDRANT_COLLECTION_PREFIX",
        mode="before",
    )
    @classmethod
    def strip_comments(cls, v: Any) -> str:
        """Strip inline comments from string values."""
        return strip_comment(v)

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, v: Any) -> int:
        """Parse PORT, stripping comments and converting to int."""
        if isinstance(v, int):
            return v
        v_str = strip_comment(str(v))
        if not v_str:
            return 8000
        try:
            return int(v_str)
        except (ValueError, TypeError):
            return 8000

    @field_validator("AUTO_CREATE_TABLES", "DROP_AND_RECREATE_TABLES", "DROP_AND_RECREATE_COLLECTIONS", "DEBUG", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        """Parse boolean values, stripping comments and converting string to bool."""
        if isinstance(v, bool):
            return v
        v_str = strip_comment(str(v)).lower()
        return v_str in ("true", "1", "yes", "on")

    @model_validator(mode="after")
    def validate_required_settings(self) -> "Settings":
        """Validate that required settings are actually set (not just defaults).
        
        This runs after the model is created and checks if critical settings
        are using placeholder/default values instead of real values from .env.
        """
        errors = []
        warnings = []

        # Check required settings
        if not self.DATABASE_URL or "user:password" in self.DATABASE_URL:
            errors.append("DATABASE_URL is not set in .env (using placeholder default)")

        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env (required for AI features)")

        if not self.QDRANT_API_KEY:
            errors.append("QDRANT_API_KEY is not set in .env (required for vector search)")

        if self.QDRANT_URL == "http://localhost:6333":
            warnings.append("QDRANT_URL is using default localhost - is this intentional?")

        # Log warnings
        for warning in warnings:
            logger.warning(f"⚠️  Configuration: {warning}")

        # Log errors (but don't fail - let the app start and fail naturally when trying to use these)
        for error in errors:
            logger.error(f"❌ Configuration Error: {error}")

        if errors:
            logger.error(
                "💡 Tip: Copy env.example to .env and update with your actual values:\n"
                "   cp env.example .env\n"
                "   # Then edit .env with your real credentials"
            )

        return self


# Create settings instance (reads from .env automatically)
settings = Settings()
