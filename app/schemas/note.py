"""Note schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    """Schema for creating a note."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    document_id: uuid.UUID | None = Field(default=None, description="Related document ID")
    note_type: str | None = Field(default=None, description="Note type")
    title: str | None = Field(default=None, description="Note title")
    body: str | None = Field(default=None, description="Note body content")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class NoteRead(BaseModel):
    """Schema for reading a note."""

    id: uuid.UUID = Field(description="Note ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    document_id: uuid.UUID | None = Field(default=None, description="Related document ID")
    note_type: str | None = Field(default=None, description="Note type")
    title: str | None = Field(default=None, description="Note title")
    body: str | None = Field(default=None, description="Note body content")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(description="Note creation timestamp")
    updated_at: datetime = Field(description="Note last update timestamp")

    model_config = ConfigDict(from_attributes=True)

