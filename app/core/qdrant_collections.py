"""Qdrant collection definitions and initialization."""
import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    PayloadSchemaType,
    VectorParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Collection names
CHUNKS_COLLECTION = "mentraflow_chunks"
CONCEPTS_COLLECTION = "mentraflow_concepts"

# Vector dimensions (matching OpenAI text-embedding-3-small)
VECTOR_SIZE = 1536


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance.
    
    Returns:
        QdrantClient instance configured from environment variables
    """
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        timeout=30,
    )


async def drop_collections() -> None:
    """Drop both Qdrant collections (use with caution - deletes all data!).
    
    This will delete all vectors and data in both collections.
    """
    import asyncio
    
    client = get_qdrant_client()
    
    # Check existing collections
    try:
        collections_result = await asyncio.wait_for(
            asyncio.to_thread(client.get_collections),
            timeout=10.0
        )
        existing_collections = {c.name for c in collections_result.collections}
    except asyncio.TimeoutError:
        logger.error("❌ Timeout checking Qdrant collections (server may be unreachable)")
        raise
    
    # Drop chunks collection if it exists
    if CHUNKS_COLLECTION in existing_collections:
        logger.warning(f"🗑️  Dropping collection: {CHUNKS_COLLECTION}")
        try:
            await asyncio.to_thread(
                client.delete_collection,
                collection_name=CHUNKS_COLLECTION,
            )
            logger.info(f"✅ Dropped collection: {CHUNKS_COLLECTION}")
        except Exception as e:
            logger.error(f"❌ Failed to drop collection {CHUNKS_COLLECTION}: {str(e)}")
            raise
    else:
        logger.info(f"ℹ️  Collection does not exist: {CHUNKS_COLLECTION}")
    
    # Drop concepts collection if it exists
    if CONCEPTS_COLLECTION in existing_collections:
        logger.warning(f"🗑️  Dropping collection: {CONCEPTS_COLLECTION}")
        try:
            await asyncio.to_thread(
                client.delete_collection,
                collection_name=CONCEPTS_COLLECTION,
            )
            logger.info(f"✅ Dropped collection: {CONCEPTS_COLLECTION}")
        except Exception as e:
            logger.error(f"❌ Failed to drop collection {CONCEPTS_COLLECTION}: {str(e)}")
            raise
    else:
        logger.info(f"ℹ️  Collection does not exist: {CONCEPTS_COLLECTION}")


async def ensure_collections_exist() -> None:
    """Ensure both Qdrant collections exist with proper configuration.
    
    Creates collections if they don't exist, no-op if they already exist.
    Also creates payload indexes for efficient filtering.
    """
    import asyncio
    
    client = get_qdrant_client()
    
    # Check existing collections (run synchronous call in thread pool)
    try:
        # 10 second timeout for collection operations
        collections_result = await asyncio.wait_for(
            asyncio.to_thread(client.get_collections),
            timeout=10.0
        )
        existing_collections = {c.name for c in collections_result.collections}
    except asyncio.TimeoutError:
        logger.error("❌ Timeout checking Qdrant collections (server may be unreachable)")
        raise
    
    # Collection configuration (shared for both)
    collection_config = {
        "vectors_config": VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
        "hnsw_config": HnswConfigDiff(
            m=16,
            ef_construct=128,
        ),
        "on_disk_payload": True,
    }
    
    # Ensure chunks collection
    if CHUNKS_COLLECTION not in existing_collections:
        logger.info(f"📦 Creating collection: {CHUNKS_COLLECTION}")
        await asyncio.to_thread(
            client.create_collection,
            collection_name=CHUNKS_COLLECTION,
            **collection_config,
        )
        logger.info(f"✅ Created collection: {CHUNKS_COLLECTION}")
    else:
        logger.info(f"ℹ️  Collection already exists: {CHUNKS_COLLECTION}")
    
    # Ensure concepts collection
    if CONCEPTS_COLLECTION not in existing_collections:
        logger.info(f"📦 Creating collection: {CONCEPTS_COLLECTION}")
        await asyncio.to_thread(
            client.create_collection,
            collection_name=CONCEPTS_COLLECTION,
            **collection_config,
        )
        logger.info(f"✅ Created collection: {CONCEPTS_COLLECTION}")
    else:
        logger.info(f"ℹ️  Collection already exists: {CONCEPTS_COLLECTION}")
    
    # Create payload indexes for efficient filtering (run in thread pool)
    await asyncio.to_thread(create_payload_indexes, client)


def create_payload_indexes(client: QdrantClient) -> None:
    """Create payload indexes for both collections.
    
    Args:
        client: Qdrant client instance
    """
    # Indexes for chunks collection
    chunks_indexes = {
        "workspace_id": PayloadSchemaType.KEYWORD,
        "document_id": PayloadSchemaType.KEYWORD,
        "chunk_id": PayloadSchemaType.KEYWORD,
        "user_id": PayloadSchemaType.KEYWORD,
        "created_at": PayloadSchemaType.INTEGER,
    }
    
    # Indexes for concepts collection
    concepts_indexes = {
        "workspace_id": PayloadSchemaType.KEYWORD,
        "concept_id": PayloadSchemaType.KEYWORD,
        "concept_name": PayloadSchemaType.KEYWORD,
        "created_at": PayloadSchemaType.INTEGER,
    }
    
    # Helper function to create indexes for a collection
    def _create_indexes(collection_name: str, indexes: dict[str, PayloadSchemaType]) -> None:
        """Create indexes for a collection with error handling."""
        for field_name, field_type in indexes.items():
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.info(f"✅ Created payload index: {collection_name}.{field_name}")
            except Exception as e:
                # Index might already exist, which is fine
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    logger.debug(f"ℹ️  Index already exists: {collection_name}.{field_name}")
                else:
                    logger.warning(f"⚠️  Failed to create index {collection_name}.{field_name}: {str(e)}")
    
    # Create indexes for both collections
    _create_indexes(CHUNKS_COLLECTION, chunks_indexes)
    _create_indexes(CONCEPTS_COLLECTION, concepts_indexes)
    
    logger.info("✅ Payload indexes creation complete")

