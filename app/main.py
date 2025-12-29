"""Main FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager

# Disable LangSmith tracing to avoid Python 3.12 compatibility issues
# This must be set before importing langchain/langgraph modules
# Note: This doesn't prevent the import, but reduces the chance of issues
if "LANGCHAIN_TRACING_V2" not in os.environ:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.qdrant_collections import ensure_collections_exist, drop_collections
from app.api.v1.router import api_router
from app.infrastructure.database import check_db_connection, create_tables, drop_tables
from app.infrastructure.qdrant import check_qdrant_connection

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Enable debug logging for specific modules in debug mode
if settings.DEBUG:
    logging.getLogger("app").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # SQL queries
    logger.info("🐛 Debug mode enabled - verbose logging active")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - runs on startup and shutdown."""
    # Startup
    logger.info("🚀 Starting MentraFlow API...")
    
    # Check database connection
    db_connected = await check_db_connection()
    if not db_connected:
        logger.warning("⚠️  Database connection check failed - application will start but DB operations may fail")
    else:
        # Optionally drop and recreate tables (development only - use with caution!)
        drop_and_recreate = os.getenv("DROP_AND_RECREATE_TABLES", "false").lower() == "true"
        auto_create = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
        
        if drop_and_recreate:
            logger.warning("⚠️  DROP_AND_RECREATE_TABLES=true - This will DELETE ALL DATA!")
            logger.warning("⚠️  Dropping all tables before recreating...")
            try:
                await drop_tables()
                await create_tables()
                logger.info("✅ Tables dropped and recreated successfully")
            except Exception as e:
                logger.error(f"❌ Failed to drop/recreate tables: {str(e)}")
                logger.warning("⚠️  Continuing without table recreation")
        elif auto_create:
            logger.info("📦 Auto-creating database tables (AUTO_CREATE_TABLES=true)")
            try:
                await create_tables()
            except Exception as e:
                logger.error(f"❌ Failed to create tables: {str(e)}")
                logger.warning("⚠️  Continuing without auto-creation - use 'make migrate' to create tables")
        else:
            logger.info("ℹ️  Auto-create tables disabled (use AUTO_CREATE_TABLES=true to enable)")
            logger.info("ℹ️  For development: set DROP_AND_RECREATE_TABLES=true to drop and recreate on startup")
            logger.info("ℹ️  Run 'make migrate' to create tables via Alembic")
    
    # Check Qdrant connection
    qdrant_connected = await check_qdrant_connection()
    if not qdrant_connected:
        logger.warning("⚠️  Qdrant connection check failed - application will start but vector operations may fail")
    else:
        logger.info("✅ Qdrant connection verified")
        
        # Optionally drop and recreate collections (development only - use with caution!)
        drop_and_recreate_collections = os.getenv("DROP_AND_RECREATE_COLLECTIONS", "false").lower() == "true"
        
        if drop_and_recreate_collections:
            logger.warning("⚠️  DROP_AND_RECREATE_COLLECTIONS=true - This will DELETE ALL VECTOR DATA!")
            logger.warning("⚠️  Dropping all collections before recreating...")
            try:
                await drop_collections()
                # Wait a moment to ensure deletion is complete
                import asyncio
                await asyncio.sleep(1)
                await ensure_collections_exist()
                logger.info("✅ Collections dropped and recreated successfully")
            except Exception as e:
                logger.error(f"❌ Failed to drop/recreate collections: {str(e)}", exc_info=True)
                logger.warning("⚠️  Continuing without collection recreation")
        else:
            # Ensure global collections exist with proper configuration
            try:
                await ensure_collections_exist()
                logger.info("✅ Qdrant collections verified/created")
            except Exception as e:
                logger.error(f"❌ Failed to ensure Qdrant collections: {str(e)}")
                logger.warning("⚠️  Continuing without collection setup - collections may need manual creation")
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down MentraFlow API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,  # Enable FastAPI debug mode
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "MentraFlow API", "version": settings.VERSION}


@app.get("/api/v1/version")
async def get_version():
    """Get API version."""
    return {"version": settings.VERSION, "api_version": "v1"}


@app.get("/health")
async def health_check():
    """Health check endpoint with database and Qdrant connection checks."""
    db_status = await check_db_connection()
    qdrant_status = await check_qdrant_connection()
    
    if not db_status or not qdrant_status:
        status_code = 503
        details = []
        if not db_status:
            details.append("Database connection unavailable")
        if not qdrant_status:
            details.append("Qdrant connection unavailable")
        
        raise HTTPException(
            status_code=status_code,
            detail="; ".join(details)
        )
    
    return {
        "status": "healthy",
        "database": "connected",
        "qdrant": "connected"
    }

