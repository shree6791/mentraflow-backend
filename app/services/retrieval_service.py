"""Retrieval service for semantic search."""
import logging
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.qdrant import QdrantClientWrapper
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service for semantic search and retrieval."""

    def __init__(
        self, db: AsyncSession, qdrant_client: QdrantClientWrapper | None = None
    ):
        """Initialize service with database session and optional Qdrant client wrapper."""
        self.db = db
        # Use singleton QdrantClientWrapper for connection pooling
        self.qdrant_client = qdrant_client or QdrantClientWrapper()

    async def _generate_query_embedding(
        self, query: str, embedding_model: str = "default"
    ) -> list[float]:
        """Generate embedding for query text using OpenAI.
        
        Args:
            query: Query text to embed
            embedding_model: Model name (default uses settings.OPENAI_EMBEDDING_MODEL)
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            ValueError: If OpenAI API key is missing or API call fails
        """
        # Use configured embedding model or default
        model = settings.OPENAI_EMBEDDING_MODEL if embedding_model == "default" else embedding_model
        
        # Validate API key
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not configured. Please set OPENAI_API_KEY in .env file."
            )
        
        try:
            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Generate embedding
            response = await client.embeddings.create(
                model=model,
                input=query,
            )
            
            # Extract vector from response
            vector = response.data[0].embedding
            
            return vector
            
        except Exception as e:
            logger.error(f"Error generating query embedding with OpenAI: {str(e)}", exc_info=True)
            raise ValueError(
                f"Failed to generate query embedding: {str(e)}. "
                f"Please check your OpenAI API key and network connection."
            ) from e

    async def semantic_search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic search and return chunk texts with citations."""
        # Generate query embedding
        query_vector = await self._generate_query_embedding(query)

        # Search Qdrant using convenience method for chunks
        # Extract document_id from filters if present
        document_id = None
        if filters and "document_id" in filters:
            document_id = filters.get("document_id")
            if isinstance(document_id, str):
                document_id = uuid.UUID(document_id)
        
        search_results = await self.qdrant_client.search_chunks(
            workspace_id=workspace_id,
            query_vector=query_vector,
            top_k=top_k,
            document_id=document_id,
        )

        # Fetch chunk details from DB (batch query to avoid N+1 problem)
        if not search_results:
            return []

        # Collect all chunk IDs
        chunk_ids = [uuid.UUID(r["payload"]["chunk_id"]) for r in search_results]
        
        # Single batch query for all chunks
        # Defense-in-depth: Validate workspace_id in DB query (Qdrant already filters, but this adds extra safety)
        from app.models.document import Document
        stmt = (
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.id.in_(chunk_ids),
                Document.workspace_id == workspace_id,  # Additional workspace validation
            )
        )
        db_result = await self.db.execute(stmt)
        chunks = db_result.scalars().all()
        
        # Create lookup dictionary for O(1) access
        chunks_by_id = {chunk.id: chunk for chunk in chunks}
        
        # Build results maintaining order from search_results
        results = []
        for result in search_results:
            chunk_id = uuid.UUID(result["payload"]["chunk_id"])
            chunk = chunks_by_id.get(chunk_id)
            
            if chunk:
                results.append(
                    {
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "score": result["score"],
                        "citation": {
                            "document_id": str(chunk.document_id),
                            "chunk_index": chunk.chunk_index,
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                        },
                    }
                )

        return results

