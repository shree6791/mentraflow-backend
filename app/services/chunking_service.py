"""Chunking service."""
import uuid
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.base import BaseService


class ChunkingService(BaseService):
    """Service for document chunking operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    def _recursive_chunk(
        self, text: str, chunk_size: int = 800, overlap: int = 120
    ) -> list[tuple[int, int, str]]:
        """Split text into chunks with overlap.
        
        Returns list of (start_char, end_char, content) tuples.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of (start_char, end_char, content) tuples
        """
        import logging
        logger = logging.getLogger(__name__)
        
        chunks = []
        start = 0
        text_length = len(text)
        
        # Safety check: prevent infinite loop if overlap >= chunk_size
        if overlap >= chunk_size:
            raise ValueError(f"Overlap ({overlap}) must be less than chunk_size ({chunk_size})")
        
        iteration = 0
        step_size = chunk_size - overlap
        max_iterations = (text_length // step_size) + 10  # Safety limit
        
        while start < text_length:
            iteration += 1
            
            # Safety check to prevent infinite loops
            if iteration > max_iterations:
                logger.error(f"Chunking exceeded max iterations ({max_iterations}). Text length: {text_length}, start: {start}")
                raise ValueError(f"Chunking exceeded max iterations. Possible infinite loop.")
            
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end]
            chunks.append((start, end, chunk_text))
            
            # Calculate next start position
            next_start = end - overlap
            if next_start <= start:
                logger.warning(f"Next start position ({next_start}) <= current start ({start}). Breaking to prevent infinite loop.")
                break
            
            start = next_start
        return chunks

    async def chunk_document(
        self,
        document_id: uuid.UUID,
        strategy: str = "recursive",
        chunk_size: int = 800,
        overlap: int = 120,
    ) -> list[DocumentChunk]:
        """Chunk a document and store chunks in database."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if not document.content:
            raise ValueError(f"Document {document_id} has no content to chunk")

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

        await self._commit_and_refresh(*chunks)
        return chunks

