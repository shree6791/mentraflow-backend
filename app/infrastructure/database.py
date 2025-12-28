"""PostgreSQL database session management."""
import logging
from urllib.parse import parse_qs, urlparse, urlunparse, urlencode

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)


def normalize_database_url(url: str) -> str:
    """Normalize database URL for asyncpg compatibility.
    
    Removes sslmode parameter (asyncpg doesn't support it).
    For asyncpg, SSL is handled automatically or via connection parameters.
    
    Args:
        url: Database URL (may contain sslmode parameter)
        
    Returns:
        Normalized URL without sslmode parameter
    """
    if "sslmode" not in url:
        return url
    
    # Parse the URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove sslmode (asyncpg doesn't support it - SSL is handled automatically)
    if "sslmode" in query_params:
        del query_params["sslmode"]
        logger.debug(f"Removed sslmode parameter from DATABASE_URL (asyncpg handles SSL automatically)")
    
    # Reconstruct URL
    new_query = urlencode(query_params, doseq=True) if query_params else ""
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))
    
    return normalized


# Normalize database URL for asyncpg compatibility
_normalized_db_url = normalize_database_url(settings.DATABASE_URL)

# Create async engine with connection pooling for better performance
engine = create_async_engine(
    _normalized_db_url,
    echo=True,
    # Connection pool configuration for reliability and scalability
    pool_size=20,  # Number of connections to maintain
    max_overflow=10,  # Additional connections beyond pool_size
    pool_pre_ping=True,  # Verify connections before using (prevents stale connections)
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models with schema support
# Use 'mentraflow' schema for better organization (instead of default 'public')
Base = declarative_base()

# Set default schema for all tables
# This ensures all tables are created in the 'mentraflow' schema
Base.metadata.schema = "mentraflow"

# Import all models AFTER Base is defined to avoid circular imports
# This ensures Base.metadata has all tables registered for create_tables() and drop_tables()
# Import at module level (not in functions) because import * is only allowed at module level
from app.models import *  # noqa: F401, F403


async def check_db_connection() -> bool:
    """Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    import asyncio
    
    async def _check():
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    
    try:
        # Add timeout to prevent hanging indefinitely (5 second timeout)
        await asyncio.wait_for(_check(), timeout=5.0)
        logger.info("✅ Database connection successful")
        return True
    except asyncio.TimeoutError:
        logger.error("❌ Database connection timeout (server may be unreachable)")
        return False
    except SQLAlchemyError as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error checking database: {str(e)}")
        return False


async def drop_tables() -> None:
    """Drop all database tables (development only - use with caution!).
    
    WARNING: This will delete all data in all tables in the 'mentraflow' schema.
    Only use in development.
    
    Note: Models are imported at module level to ensure Base.metadata has all tables.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        schema_name = Base.metadata.schema or "public"
        logger.info(f"🗑️  Database tables dropped successfully from schema '{schema_name}'")
    except SQLAlchemyError as e:
        logger.error(f"❌ Failed to drop tables: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error dropping tables: {str(e)}")
        raise


async def create_tables() -> None:
    """Create all tables defined in models.
    
    Creates tables in the 'mentraflow' schema. If the schema doesn't exist,
    it will be created automatically.
    
    Note: This is useful for development/testing. In production,
    use Alembic migrations instead.
    
    Note: Models are imported at module level to ensure Base.metadata has all tables.
    """
    try:
        async with engine.begin() as conn:
            # Create schema if it doesn't exist
            schema_name = Base.metadata.schema or "public"
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            logger.info(f"✅ Schema '{schema_name}' verified/created")
            
            # Create all tables in the schema
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"✅ Database tables created successfully in schema '{Base.metadata.schema}'")
    except SQLAlchemyError as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating tables: {str(e)}")
        raise


async def get_db() -> AsyncSession:
    """Dependency to get database session.
    
    Sets search_path to 'mentraflow' schema so all queries use it automatically.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set search_path to mentraflow schema for this session
            await session.execute(text("SET search_path TO mentraflow, public"))
            yield session
        finally:
            await session.close()

