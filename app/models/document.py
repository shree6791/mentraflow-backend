"""Document model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.document_chunk import DocumentChunk
    from app.models.flashcard import Flashcard
    from app.models.note import Note


class Document(Base):
    """Document model."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_workspace_id", "workspace_id"),
        Index("ix_documents_created_by", "created_by"),
        Index("ix_documents_status", "status"),  # For filtering documents by status (pending, processed, etc.)
        Index("ix_documents_workspace_status", "workspace_id", "status"),  # Composite for workspace + status filtering
        Index("ix_documents_content_hash", "content_hash"),  # For deduplication lookups
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)  # SHA-256 hash of content for deduplication
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # Auto-generated summary after ingest
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )  # Last agent run ID (for tracking async progress)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="documents"
    )
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_documents", foreign_keys=[created_by]
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    flashcards: Mapped[list["Flashcard"]] = relationship(
        "Flashcard", back_populates="document"
    )
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="document")

