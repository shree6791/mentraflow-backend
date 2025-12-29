"""Embedding service."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.qdrant import QdrantClientWrapper
from app.models.document_chunk import DocumentChunk
from app.models.embedding import Embedding
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class EmbeddingService(BaseService):
    """Service for generating and storing embeddings."""

    def __init__(
        self, db: AsyncSession, qdrant_client: QdrantClientWrapper | None = None
    ):
        """Initialize service with database session and optional Qdrant client wrapper."""
        super().__init__(db)
        # Use singleton QdrantClientWrapper for connection pooling
        self.qdrant_client = qdrant_client or QdrantClientWrapper()

    async def _generate_embedding(
        self, text: str, embedding_model: str = "default"
    ) -> tuple[list[float], int]:
        """Generate embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            embedding_model: Model name (default uses settings.OPENAI_EMBEDDING_MODEL)
            
        Returns:
            Tuple of (vector, dimensions)
            
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
        
        # Model dimensions mapping
        model_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        expected_dims = model_dims.get(model, 1536)  # Default to 1536
        
        try:
            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Generate embedding
            response = await client.embeddings.create(
                model=model,
                input=text,
            )
            
            # Extract vector from response
            vector = response.data[0].embedding
            actual_dims = len(vector)
            
            # Validate dimensions match expected
            if actual_dims != expected_dims:
                logger.warning(
                    f"Embedding dimensions mismatch: expected {expected_dims}, got {actual_dims} "
                    f"for model {model}. Using actual dimensions."
                )
            
            return vector, actual_dims
            
        except Exception as e:
            logger.error(f"Error generating embedding with OpenAI: {str(e)}", exc_info=True)
            raise ValueError(
                f"Failed to generate embedding: {str(e)}. "
                f"Please check your OpenAI API key and network connection."
            ) from e

    async def embed_chunks(
        self, document_id: uuid.UUID, embedding_model: str = "default"
    ) -> list[Embedding]:
        """Embed chunks for a document and store in DB + Qdrant.
        
        This method:
        1. Fetches chunks from database
        2. Generates embeddings using OpenAI
        3. Stores embeddings in database
        4. Upserts vectors to Qdrant
        """
        # Get document to access workspace_id
        from app.models.document import Document
        doc_stmt = select(Document).where(Document.id == document_id)
        doc_result = await self.db.execute(doc_stmt)
        document = doc_result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        workspace_id = document.workspace_id

        # Get chunks
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.db.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            raise ValueError(f"No chunks found for document {document_id}")

        # Generate embeddings in batch for efficiency
        # OpenAI supports up to 2048 inputs per batch request
        model = settings.OPENAI_EMBEDDING_MODEL if embedding_model == "default" else embedding_model
        
        # Validate API key
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not configured. Please set OPENAI_API_KEY in .env file."
            )
        
        # Prepare texts for batch embedding
        chunk_texts = [chunk.content or "" for chunk in chunks]
        
        # Generate embeddings in batch
        try:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # OpenAI supports batch requests (up to 2048 inputs)
            # Process in batches of 100 to avoid token limits
            batch_size = 100
            all_vectors = []
            vector_size = None
            
            for i in range(0, len(chunk_texts), batch_size):
                batch_texts = chunk_texts[i:i + batch_size]
                
                response = await client.embeddings.create(
                    model=model,
                    input=batch_texts,
                )
                
                # Extract vectors from response
                batch_vectors = [item.embedding for item in response.data]
                all_vectors.extend(batch_vectors)
                
                # Set vector size from first batch
                if vector_size is None and batch_vectors:
                    vector_size = len(batch_vectors[0])
            
            if not all_vectors or len(all_vectors) != len(chunks):
                raise ValueError(
                    f"Embedding generation failed: expected {len(chunks)} vectors, "
                    f"got {len(all_vectors)}"
                )
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings with OpenAI: {str(e)}", exc_info=True)
            raise ValueError(
                f"Failed to generate embeddings: {str(e)}. "
                f"Please check your OpenAI API key and network connection."
            ) from e

        # Create embedding records and Qdrant points
        embeddings = []
        points_to_upsert = []
        
        for idx, chunk in enumerate(chunks):
            vector = all_vectors[idx]
            dims = len(vector)
            
            # Create embedding record
            embedding = Embedding(
                workspace_id=workspace_id,
                entity_type="document_chunk",
                entity_id=chunk.id,
                model=embedding_model,
                dims=dims,
                vector_store="qdrant",
                collection=self.qdrant_client.get_collection_name("chunks"),
                vector_id=str(chunk.id),
                status="generated",
            )
            self.db.add(embedding)
            embeddings.append(embedding)

            # Prepare Qdrant point (using wrapper's expected format)
            # Payload schema: workspace_id, document_id, chunk_id, chunk_index, created_at
            points_to_upsert.append(
                {
                    "id": str(chunk.id),  # Point ID = chunk_id
                    "vector": vector,
                    "payload": {
                        "workspace_id": str(workspace_id),
                        "document_id": str(document_id),
                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,
                        "created_at": int(datetime.now(timezone.utc).timestamp()),  # Unix timestamp
                        # Optional fields
                        "text": chunk.content[:500] if chunk.content else None,  # Snippet (first 500 chars)
                    },
                }
            )

        # Commit embeddings to DB first (source of truth)
        await self._commit_and_refresh(*embeddings)

        # Upsert to Qdrant using convenience method for chunks
        # Note: Qdrant errors are handled by QdrantClientWrapper
        if points_to_upsert and vector_size:
            await self.qdrant_client.upsert_chunk_vectors(
                workspace_id=workspace_id,
                points=points_to_upsert,
            )

        return embeddings

    async def reindex_document(
        self, document_id: uuid.UUID, embedding_model: str = "default"
    ) -> list[Embedding]:
        """Reindex a document: delete old embeddings and regenerate with new model.
        
        This method:
        1. Deletes old embeddings from Qdrant (by document_id filter)
        2. Deletes old Embedding records from DB
        3. Re-runs embedding generation
        4. Upserts new vectors to Qdrant
        
        Args:
            document_id: Document ID to reindex
            embedding_model: Embedding model to use (default: "default")
            
        Returns:
            List of new embeddings created
        """
        # Get document to access workspace_id
        from app.models.document import Document
        doc_stmt = select(Document).where(Document.id == document_id)
        doc_result = await self.db.execute(doc_stmt)
        document = doc_result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        workspace_id = document.workspace_id

        # Get all chunks for this document
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.db.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            raise ValueError(f"No chunks found for document {document_id}")

        # Get old embeddings to delete
        old_embeddings_stmt = select(Embedding).where(
            Embedding.workspace_id == workspace_id,
            Embedding.entity_type == "document_chunk",
            Embedding.entity_id.in_([chunk.id for chunk in chunks]),
        )
        old_embeddings_result = await self.db.execute(old_embeddings_stmt)
        old_embeddings = list(old_embeddings_result.scalars().all())

        # Delete old embeddings from Qdrant
        if old_embeddings:
            # Get collection name
            collection_name = self.qdrant_client.get_collection_name("chunks")
            
            # Delete points by chunk IDs (point IDs = chunk IDs)
            chunk_ids_to_delete = [str(emb.entity_id) for emb in old_embeddings]
            if chunk_ids_to_delete:
                from qdrant_client.models import PointIdsList
                self.qdrant_client.client.delete(
                    collection_name=collection_name,
                    points_selector=PointIdsList(points=chunk_ids_to_delete),
                )

        # Delete old embedding records from DB
        for old_emb in old_embeddings:
            await self.db.delete(old_emb)
        
        await self.db.commit()

        # Regenerate embeddings (this will create new DB records and upsert to Qdrant)
        # Note: embed_chunks handles its own error handling
        new_embeddings = await self.embed_chunks(document_id, embedding_model)

        return new_embeddings

