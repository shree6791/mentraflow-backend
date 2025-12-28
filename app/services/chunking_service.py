"""Chunking service."""
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class ChunkingService:
    """Service for document chunking operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    def _recursive_chunk(
        self, text: str, chunk_size: int = 800, overlap: int = 120
    ) -> list[tuple[int, int, str]]:
        """Split text into chunks with overlap.
        
        Returns list of (start_char, end_char, content) tuples.
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end]
            chunks.append((start, end, chunk_text))
            start = end - overlap  # Overlap for next chunk

        return chunks

    async def chunk_document(
        self,
        document_id: uuid.UUID,
        strategy: str = "recursive",
        chunk_size: int = 800,
        overlap: int = 120,
    ) -> list[DocumentChunk]:
        """Chunk a document and store chunks in database."""
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if not document.content:
            raise ValueError(f"Document {document_id} has no content to chunk")

        try:
            # Delete existing chunks
            delete_stmt = delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
            await self.db.execute(delete_stmt)

            # Generate chunks
            if strategy == "recursive":
                chunk_data = self._recursive_chunk(
                    document.content, chunk_size=chunk_size, overlap=overlap
                )
            else:
                raise ValueError(f"Unknown chunking strategy: {strategy}")

            # Create chunk records
            chunks = []
            for idx, (start_char, end_char, content) in enumerate(chunk_data):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    start_char=start_char,
                    end_char=end_char,
                    content=content,
                )
                self.db.add(chunk)
                chunks.append(chunk)

            await self.db.commit()
            for chunk in chunks:
                await self.db.refresh(chunk)

            return chunks
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while chunking document: {str(e)}") from e

