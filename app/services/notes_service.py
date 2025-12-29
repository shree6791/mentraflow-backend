"""Notes service."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.services.base import BaseService


class NotesService(BaseService):
    """Service for note operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_note(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        source_document_id: uuid.UUID | None = None,
        note_type: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Note:
        """Create a new note."""
        note = Note(
            workspace_id=workspace_id,
            user_id=user_id,
            document_id=source_document_id,
            note_type=note_type,
            title=title,
            body=content,
            meta_data=metadata,
        )
        self.db.add(note)
        await self._commit_and_refresh(note)
        return note

    async def list_notes(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> list[Note]:
        """List notes in a workspace, optionally filtered by user."""
        stmt = select(Note).where(Note.workspace_id == workspace_id)
        if user_id:
            stmt = stmt.where(Note.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

