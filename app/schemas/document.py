"""Document schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    title: str | None = Field(default=None, description="Document title")
    doc_type: str | None = Field(default=None, description="Document type")
    source_url: str | None = Field(default=None, description="Source URL")
    language: str | None = Field(default=None, description="Document language")
    content: str | None = Field(default=None, description="Document content")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class DocumentRead(BaseModel):
    """Schema for reading a document."""

    id: uuid.UUID = Field(description="Document ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    created_by: uuid.UUID | None = Field(default=None, description="Creator user ID (nullable if user deleted)")
    title: str | None = Field(default=None, description="Document title")
    doc_type: str | None = Field(default=None, description="Document type")
    source_url: str | None = Field(default=None, description="Source URL")
    language: str | None = Field(default=None, description="Document language")
    status: str | None = Field(default=None, description="Document processing status")
    content: str | None = Field(default=None, description="Document content")
    summary_text: str | None = Field(default=None, description="Auto-generated summary")
    last_run_id: uuid.UUID | None = Field(default=None, description="Last agent run ID")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(description="Document creation timestamp")
    updated_at: datetime = Field(description="Document last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusUpdate(BaseModel):
    """Schema for updating document status."""

    status: str = Field(description="New document status")

