"""Infrastructure layer for external service integrations.

This module contains wrappers and clients for external infrastructure services
such as databases (PostgreSQL, Qdrant), message queues, caching layers, etc.
"""
from app.infrastructure.database import (
    Base,
    engine,
    AsyncSessionLocal,
    get_db,
    check_db_connection,
    create_tables,
    drop_tables,
    normalize_database_url,
)
from app.infrastructure.qdrant import QdrantClientWrapper, qdrant_client, check_qdrant_connection

__all__ = [
    # Database (PostgreSQL)
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "check_db_connection",
    "create_tables",
    "drop_tables",
    "normalize_database_url",
    # Vector Database (Qdrant)
    "QdrantClientWrapper",
    "qdrant_client",
    "check_qdrant_connection",
]

