"""Notes endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse
from app.schemas.note import NoteCreate, NoteRead
from app.services.notes_service import NotesService

router = APIRouter()


class NoteUpdate(BaseModel):
    """Schema for updating a note."""
    title: str | None = Field(default=None)
    body: str | None = Field(default=None)
    note_type: str | None = Field(default=None)
    metadata: dict | None = Field(default=None)


@router.post(
    "/notes",
    response_model=NoteRead,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create a new note",
)
async def create_note(
    request: NoteCreate,
    user_id: Annotated[uuid.UUID, Query(description="User ID")],  # TODO: Get from auth
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NoteRead:
    """Create a new note."""
    try:
        service = NotesService(db)
        note = await service.create_note(
            workspace_id=request.workspace_id,
            user_id=user_id,
            content=request.body or "",
            source_document_id=request.document_id,
            note_type=request.note_type,
            title=request.title,
            meta_data=request.metadata,
        )
        return NoteRead.model_validate(note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}")


@router.get(
    "/notes",
    response_model=list[NoteRead],
    responses={500: {"model": ErrorResponse}},
    summary="List notes",
)
async def list_notes(
    workspace_id: Annotated[uuid.UUID, Query(description="Workspace ID")],
    document_id: Annotated[uuid.UUID | None, Query(description="Filter by document ID")] = None,
    user_id: Annotated[uuid.UUID | None, Query(description="Filter by user ID")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[NoteRead]:
    """List notes, optionally filtered by document or user."""
    try:
        service = NotesService(db)
        notes = await service.list_notes(workspace_id=workspace_id, user_id=user_id)
        # TODO: Add document_id filtering to service
        if document_id:
            notes = [n for n in notes if n.document_id == document_id]
        return [NoteRead.model_validate(n) for n in notes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing notes: {str(e)}")


@router.get(
    "/notes/{note_id}",
    response_model=NoteRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get a note",
)
async def get_note(
    note_id: Annotated[uuid.UUID, Path(description="Note ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NoteRead:
    """Get a note by ID."""
    try:
        from sqlalchemy import select
        from app.models.note import Note
        
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
        return NoteRead.model_validate(note)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting note: {str(e)}")


@router.patch(
    "/notes/{note_id}",
    response_model=NoteRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update a note",
)
async def update_note(
    note_id: Annotated[uuid.UUID, Path(description="Note ID")],
    request: NoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NoteRead:
    """Update a note."""
    try:
        from sqlalchemy import select
        from app.models.note import Note
        
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
        
        if request.title is not None:
            note.title = request.title
        if request.body is not None:
            note.body = request.body
        if request.note_type is not None:
            note.note_type = request.note_type
        if request.metadata is not None:
            note.meta_data = request.metadata
        
        await db.commit()
        await db.refresh(note)
        return NoteRead.model_validate(note)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}")


@router.delete(
    "/notes/{note_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete a note",
)
async def delete_note(
    note_id: Annotated[uuid.UUID, Path(description="Note ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a note."""
    try:
        from sqlalchemy import select
        from app.models.note import Note
        
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
        
        await db.delete(note)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")

