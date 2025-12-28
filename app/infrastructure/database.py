"""PostgreSQL database session management."""
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine with connection pooling for better performance
engine = create_async_engine(
    settings.DATABASE_URL,
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

# Base class for models
Base = declarative_base()


async def check_db_connection() -> bool:
    """Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error checking database: {str(e)}")
        return False


async def drop_tables() -> None:
    """Drop all database tables (development only - use with caution!).
    
    WARNING: This will delete all data in all tables. Only use in development.
    """
    try:
        # Import all models to ensure Base.metadata has all tables
        from app.models import *  # noqa: F401, F403
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("🗑️  Database tables dropped successfully")
    except SQLAlchemyError as e:
        logger.error(f"❌ Failed to drop tables: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error dropping tables: {str(e)}")
        raise


async def create_tables() -> None:
    """Create all tables defined in models.
    
    Note: This is useful for development/testing. In production,
    use Alembic migrations instead.
    """
    try:
        # Import all models to ensure Base.metadata has all tables
        from app.models import *  # noqa: F401, F403
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating tables: {str(e)}")
        raise


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

