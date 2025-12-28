"""Qdrant client wrapper for vector storage."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.qdrant_collections import (
    CHUNKS_COLLECTION,
    CONCEPTS_COLLECTION,
    get_qdrant_client,
)

logger = logging.getLogger(__name__)


class QdrantClientWrapper:
    """Wrapper for Qdrant client with global collections.
    
    Uses global collections (mentraflow_chunks, mentraflow_concepts) with
    workspace_id in payload for filtering. Singleton pattern ensures single
    connection pool across all services, improving reliability, scalability,
    and reducing latency.
    """

    _instance: "QdrantClientWrapper | None" = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Qdrant client wrapper (only once due to singleton pattern)."""
        if self._initialized:
            return

        # Use centralized client getter
        self.client = get_qdrant_client()
        self._initialized = True

    def get_collection_name(self, collection_type: str = "chunks") -> str:
        """Get collection name for a collection type.
        
        Args:
            collection_type: Type of collection - "chunks" or "concepts"
            
        Returns:
            Collection name ("mentraflow_chunks" or "mentraflow_concepts")
        """
        if collection_type == "chunks":
            return CHUNKS_COLLECTION
        elif collection_type == "concepts":
            return CONCEPTS_COLLECTION
        else:
            raise ValueError(f"Invalid collection_type: {collection_type}. Must be 'chunks' or 'concepts'")

    async def ensure_collection(
        self,
        workspace_id: uuid.UUID,
        vector_size: int,
        distance: str = "Cosine",
        collection_type: str = "chunks",
    ) -> None:
        """Ensure a collection exists (no-op, collections are managed globally).
        
        This method is kept for backward compatibility but collections are now
        managed globally via ensure_collections_exist() in qdrant_collections.py.
        
        Args:
            workspace_id: Workspace UUID (kept for compatibility, not used)
            vector_size: Dimension of vectors (kept for compatibility, not used)
            distance: Distance metric (kept for compatibility, not used)
            collection_type: Type of collection - "chunks" or "concepts" (default: "chunks")
        """
        # Collections are now global and managed separately
        # This method is a no-op for backward compatibility
        pass

    async def upsert_points(
        self,
        workspace_id: uuid.UUID,
        points: list[dict[str, Any]],
        collection_type: str = "chunks",
    ) -> None:
        """Upsert points to a collection.
        
        Args:
            workspace_id: Workspace UUID (added to payload for filtering)
            points: List of point dictionaries with:
                - id: Point ID (string UUID - chunk_id or concept_id)
                - vector: Vector as list of floats (1536 dimensions)
                - payload: Dictionary with required fields:
                    - For chunks: workspace_id, document_id, chunk_id, chunk_index, created_at
                      Optional: user_id, text, source
                    - For concepts: workspace_id, concept_id, name, created_at
                      Optional: description, source_document_id
            collection_type: Type of collection - "chunks" or "concepts" (default: "chunks")
        """
        collection_name = self.get_collection_name(collection_type)
        
        # Validate and prepare points
        point_structs = []
        for point in points:
            # Prepare payload (copy to avoid mutating original)
            payload = point.get("payload", {}).copy()
            
            # Ensure workspace_id is set (required for filtering)
            if "workspace_id" not in payload:
                payload["workspace_id"] = str(workspace_id)
            
            # Validate required fields based on collection type
            if collection_type == "chunks":
                required_fields = ["document_id", "chunk_id", "chunk_index"]
                for field in required_fields:
                    if field not in payload:
                        raise ValueError(f"payload must include '{field}' for chunks")
            elif collection_type == "concepts":
                if "concept_id" not in payload:
                    raise ValueError("payload must include 'concept_id' for concepts")
                if "name" not in payload:
                    raise ValueError("payload must include 'name' for concepts")
            
            # Convert created_at to unix timestamp if needed
            if "created_at" not in payload:
                payload["created_at"] = int(datetime.now(timezone.utc).timestamp())
            elif isinstance(payload["created_at"], str):
                # Convert ISO string to unix timestamp
                try:
                    dt = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
                    payload["created_at"] = int(dt.timestamp())
                except (ValueError, AttributeError):
                    # Fallback to current timestamp if parsing fails
                    payload["created_at"] = int(datetime.now(timezone.utc).timestamp())
            elif isinstance(payload["created_at"], datetime):
                payload["created_at"] = int(payload["created_at"].timestamp())

            # Convert UUIDs to strings in payload
            payload = {
                k: str(v) if isinstance(v, uuid.UUID) else v
                for k, v in payload.items()
            }
            
            # For concepts: ensure concept_name is set from name (for indexing)
            if collection_type == "concepts" and "name" in payload:
                payload["concept_name"] = payload["name"]

            point_structs.append(
                PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=payload,
                )
            )

        # Upsert points
        self.client.upsert(collection_name=collection_name, points=point_structs)

    async def search(
        self,
        workspace_id: uuid.UUID,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        collection_type: str = "chunks",
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in a collection.
        
        Args:
            workspace_id: Workspace UUID (automatically added to filters)
            vector: Query vector (1536 dimensions)
            top_k: Number of results to return
            filters: Optional filters (e.g., {"document_id": "uuid"} for chunks, {"concept_id": "uuid"} for concepts)
            collection_type: Type of collection - "chunks" or "concepts" (default: "chunks")
            
        Returns:
            List of search results with score, id, and payload
        """
        collection_name = self.get_collection_name(collection_type)

        # Build filter - always include workspace_id, plus any additional filters
        conditions = []
        
        # Always filter by workspace_id for security/isolation
        conditions.append(
            FieldCondition(
                key="workspace_id",
                match=MatchValue(value=str(workspace_id)),
            )
        )
        
        # Add additional filters if provided
        if filters:
            for key, value in filters.items():
                # Convert UUID to string if needed
                match_value = str(value) if isinstance(value, uuid.UUID) else value
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=match_value),
                    )
                )
        
        qdrant_filter = Filter(must=conditions) if conditions else None

        # Perform search
        search_results = self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=top_k,
            query_filter=qdrant_filter,
        )

        # Convert to list of dictionaries
        results = []
        for result in search_results:
            results.append(
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                }
            )

        return results

    # Convenience methods for chunks collection
    async def upsert_chunk_vectors(
        self,
        workspace_id: uuid.UUID,
        points: list[dict[str, Any]],
    ) -> None:
        """Upsert chunk vectors to the chunks collection.
        
        Args:
            workspace_id: Workspace UUID
            points: List of point dictionaries with:
                - id: Point ID (string UUID - chunk_id)
                - vector: Vector as list of floats (1536 dimensions)
                - payload: Dictionary with required fields:
                    - workspace_id, document_id, chunk_id, chunk_index, created_at
                    - Optional: user_id, text, source
        """
        await self.upsert_points(
            workspace_id=workspace_id,
            points=points,
            collection_type="chunks",
        )

    async def search_chunks(
        self,
        workspace_id: uuid.UUID,
        query_vector: list[float],
        top_k: int = 8,
        document_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks in the chunks collection.
        
        Args:
            workspace_id: Workspace UUID (always filtered)
            query_vector: Query vector (1536 dimensions)
            top_k: Number of results to return (default: 8)
            document_id: Optional document ID filter
            
        Returns:
            List of search results with score, id, and payload
        """
        filters = {}
        if document_id:
            filters["document_id"] = str(document_id)
        
        return await self.search(
            workspace_id=workspace_id,
            vector=query_vector,
            top_k=top_k,
            filters=filters if filters else None,
            collection_type="chunks",
        )

    # Convenience methods for concepts collection
    async def upsert_concept_vectors(
        self,
        workspace_id: uuid.UUID,
        points: list[dict[str, Any]],
    ) -> None:
        """Upsert concept vectors to the concepts collection.
        
        Args:
            workspace_id: Workspace UUID
            points: List of point dictionaries with:
                - id: Point ID (string UUID - concept_id)
                - vector: Vector as list of floats (1536 dimensions)
                - payload: Dictionary with required fields:
                    - workspace_id, concept_id, name, created_at
                    - Optional: description, source_document_id
        """
        await self.upsert_points(
            workspace_id=workspace_id,
            points=points,
            collection_type="concepts",
        )

    async def search_concepts(
        self,
        workspace_id: uuid.UUID,
        query_vector: list[float],
        top_k: int = 10,
        name_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar concepts in the concepts collection.
        
        Args:
            workspace_id: Workspace UUID (always filtered)
            query_vector: Query vector (1536 dimensions)
            top_k: Number of results to return (default: 10)
            name_prefix: Optional concept name prefix filter (exact match on concept_name keyword)
            
        Returns:
            List of search results with score, id, and payload
        """
        filters = {}
        if name_prefix:
            # Use exact match on concept_name (keyword index)
            # Note: For prefix matching, we'd need to use a different approach
            # (e.g., text index with regex or post-filtering), but for now
            # we use exact match on the keyword field
            filters["concept_name"] = name_prefix
        
        return await self.search(
            workspace_id=workspace_id,
            vector=query_vector,
            top_k=top_k,
            filters=filters if filters else None,
            collection_type="concepts",
        )


# Global instance
qdrant_client = QdrantClientWrapper()


async def check_qdrant_connection() -> bool:
    """Check if Qdrant connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        # Try to get collections list (simple operation to test connection)
        qdrant_client.client.get_collections()
        logger.info("✅ Qdrant connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {str(e)}")
        return False

