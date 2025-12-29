"""Document service."""
import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.base import BaseService


class DocumentService(BaseService):
    """Service for document operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_document(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        source_type: str | None = None,
        source_uri: str | None = None,
        metadata: dict[str, Any] | None = None,
        raw_text: str | None = None,
        check_duplicate: bool = False,
    ) -> Document:
        """Create a new document.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            title: Document title
            source_type: Document type
            source_uri: Source URI
            metadata: Optional metadata
            raw_text: Optional raw text content (if provided, content_hash will be computed)
            check_duplicate: If True and raw_text is provided, check for duplicate by content_hash
            
        Returns:
            Created document (or existing duplicate if check_duplicate=True and duplicate found)
            
        Raises:
            ValueError: If check_duplicate=True, raw_text is provided, and duplicate exists
                        (caller can handle this to return existing document instead)
        """
        content_hash = None
        if raw_text:
            content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            
            # Check for duplicate if requested
            if check_duplicate:
                existing = await self.find_duplicate_by_hash(workspace_id, content_hash)
                if existing:
                    # Return existing document instead of creating duplicate
                    return existing
        
        document = Document(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title,
            doc_type=source_type,
            source_url=source_uri,
            meta_data=metadata,
            status="pending",
            content_hash=content_hash,
        )
        self.db.add(document)
        await self._commit_and_refresh(document)
        return document

    async def store_raw_text(self, document_id: uuid.UUID, raw_text: str) -> Document:
        """Store raw text content in a document and compute content hash."""
        document = await self.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.content = raw_text
        # Compute content hash for deduplication
        document.content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        document.status = "processed"
        await self._commit_and_refresh(document)
        return document

    async def list_documents(self, workspace_id: uuid.UUID) -> list[Document]:
        """List all documents in a workspace."""
        stmt = select(Document).where(Document.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        """Get a document by ID."""
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_document(
        self,
        document_id: uuid.UUID,
        title: str | None = None,
        doc_type: str | None = None,
        source_url: str | None = None,
        language: str | None = None,
        status: str | None = None,
        summary_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Update a document."""
        document = await self.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        if title is not None:
            document.title = title
        if doc_type is not None:
            document.doc_type = doc_type
        if source_url is not None:
            document.source_url = source_url
        if language is not None:
            document.language = language
        if status is not None:
            document.status = status
        if summary_text is not None:
            document.summary_text = summary_text
        if metadata is not None:
            document.meta_data = metadata
        
        await self._commit_and_refresh(document)
        return document

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """Delete a document (cascade deletes chunks, embeddings, etc.)."""
        document = await self.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        await self.db.delete(document)
        await self.db.commit()

    async def find_duplicate_by_hash(
        self, workspace_id: uuid.UUID, content_hash: str
    ) -> Document | None:
        """Find a document with the same content hash in the workspace.
        
        Args:
            workspace_id: Workspace ID to search in
            content_hash: SHA-256 hash of document content
            
        Returns:
            Existing document with same hash, or None if not found
        """
        stmt = (
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .where(Document.content_hash == content_hash)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

