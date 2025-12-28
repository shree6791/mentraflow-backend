"""LangChain tools wrappers for services."""
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chunking_service import ChunkingService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.flashcard_service import FlashcardService
from app.services.kg_service import KGService
from app.services.notes_service import NotesService
from app.services.retrieval_service import RetrievalService


class ServiceTools:
    """Wrapper class to hold service instances and create tools."""

    def __init__(self, db: AsyncSession):
        """Initialize service tools with database session."""
        self.db = db
        self.document_service = DocumentService(db)
        self.chunking_service = ChunkingService(db)
        self.embedding_service = EmbeddingService(db)
        self.retrieval_service = RetrievalService(db)
        self.notes_service = NotesService(db)
        self.flashcard_service = FlashcardService(db)
        self.kg_service = KGService(db)

    def get_tools(self) -> list:
        """Get list of LangChain tools."""
        return [
            self.store_raw_text,
            self.chunk_document,
            self.embed_chunks,
            self.semantic_search,
            self.create_note,
            self.create_flashcards,
            self.upsert_concepts,
            self.upsert_edges,
        ]

    @tool
    async def store_raw_text(self, document_id: str, raw_text: str) -> dict[str, Any]:
        """Store raw text content in a document.

        Args:
            document_id: UUID of the document
            raw_text: Raw text content to store

        Returns:
            Document information
        """
        import uuid

        doc = await self.document_service.store_raw_text(
            uuid.UUID(document_id), raw_text
        )
        return {
            "document_id": str(doc.id),
            "status": doc.status,
            "has_content": bool(doc.content),
        }

    @tool
    async def chunk_document(
        self,
        document_id: str,
        chunk_size: int = 800,
        overlap: int = 120,
    ) -> dict[str, Any]:
        """Chunk a document into smaller pieces.

        Args:
            document_id: UUID of the document
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters

        Returns:
            Chunking results
        """
        import uuid

        chunks = await self.chunking_service.chunk_document(
            uuid.UUID(document_id),
            strategy="recursive",
            chunk_size=chunk_size,
            overlap=overlap,
        )
        return {
            "document_id": document_id,
            "chunks_created": len(chunks),
            "chunk_size": chunk_size,
            "overlap": overlap,
        }

    @tool
    async def embed_chunks(
        self, document_id: str, embedding_model: str = "default"
    ) -> dict[str, Any]:
        """Generate embeddings for document chunks.

        Args:
            document_id: UUID of the document
            embedding_model: Model name for embeddings

        Returns:
            Embedding results
        """
        import uuid

        embeddings = await self.embedding_service.embed_chunks(
            uuid.UUID(document_id), embedding_model
        )
        return {
            "document_id": document_id,
            "embeddings_created": len(embeddings),
            "model": embedding_model,
        }

    @tool
    async def semantic_search(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 8,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform semantic search to find relevant chunks.

        Args:
            workspace_id: UUID of the workspace
            query: Search query
            top_k: Number of results to return
            document_id: Optional document ID to filter by

        Returns:
            Search results with chunks and citations
        """
        import uuid

        filters = {}
        if document_id:
            filters["document_id"] = document_id

        results = await self.retrieval_service.semantic_search(
            uuid.UUID(workspace_id), query, top_k=top_k, filters=filters
        )
        return {
            "query": query,
            "results_count": len(results),
            "results": results,
        }

    @tool
    async def create_note(
        self,
        workspace_id: str,
        user_id: str,
        content: str,
        title: str | None = None,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a note.

        Args:
            workspace_id: UUID of the workspace
            user_id: UUID of the user
            content: Note content
            title: Optional note title
            document_id: Optional related document ID

        Returns:
            Created note information
        """
        import uuid

        note = await self.notes_service.create_note(
            uuid.UUID(workspace_id),
            uuid.UUID(user_id),
            content,
            source_document_id=uuid.UUID(document_id) if document_id else None,
            title=title,
        )
        return {
            "note_id": str(note.id),
            "title": note.title,
            "created": True,
        }

    @tool
    async def create_flashcards(
        self,
        workspace_id: str,
        user_id: str,
        cards: list[dict[str, Any]],
        document_id: str | None = None,
    ) -> dict[str, Any]:
        """Create flashcards from card data.

        Args:
            workspace_id: UUID of the workspace
            user_id: UUID of the user
            cards: List of card dictionaries with front/back
            document_id: Optional source document ID

        Returns:
            Created flashcards information
        """
        import uuid

        flashcards = await self.flashcard_service.create_flashcards_from_text(
            uuid.UUID(workspace_id),
            uuid.UUID(user_id),
            uuid.UUID(document_id) if document_id else None,
            cards,
        )
        return {
            "flashcards_created": len(flashcards),
            "flashcard_ids": [str(f.id) for f in flashcards],
        }

    @tool
    async def upsert_concepts(
        self,
        workspace_id: str,
        user_id: str,
        concepts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Upsert concepts in the knowledge graph.

        Args:
            workspace_id: UUID of the workspace
            user_id: UUID of the user
            concepts: List of concept dictionaries

        Returns:
            Upserted concepts information
        """
        import uuid

        result_concepts = await self.kg_service.upsert_concepts(
            uuid.UUID(workspace_id), uuid.UUID(user_id), concepts
        )
        return {
            "concepts_written": len(result_concepts),
            "concept_ids": [str(c.id) for c in result_concepts],
        }

    @tool
    async def upsert_edges(
        self,
        workspace_id: str,
        user_id: str,
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Upsert edges in the knowledge graph.

        Args:
            workspace_id: UUID of the workspace
            user_id: UUID of the user
            edges: List of edge dictionaries

        Returns:
            Upserted edges information
        """
        import uuid

        result_edges = await self.kg_service.upsert_edges(
            uuid.UUID(workspace_id), uuid.UUID(user_id), edges
        )
        return {
            "edges_written": len(result_edges),
            "edge_ids": [str(e.id) for e in result_edges],
        }

