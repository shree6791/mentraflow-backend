"""Note model."""
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
    from app.models.document import Document


class Note(Base):
    """Note model."""

    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_workspace_id", "workspace_id"),
        Index("ix_notes_user_id", "user_id"),
        Index("ix_notes_document_id", "document_id"),
        Index("ix_notes_note_type", "note_type"),  # For filtering by note type
        Index("ix_notes_workspace_user", "workspace_id", "user_id"),  # Composite for workspace + user queries
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    note_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, name="metadata")
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
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="notes")
    user: Mapped["User"] = relationship("User", back_populates="notes")
    document: Mapped["Document | None"] = relationship(
        "Document", back_populates="notes"
    )

