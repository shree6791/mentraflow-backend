"""Flashcard model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.document import Document
    from app.models.flashcard_review import FlashcardReview
    from app.models.flashcard_srs_state import FlashcardSRSState


class Flashcard(Base):
    """Flashcard model."""

    __tablename__ = "flashcards"
    __table_args__ = (
        Index("ix_flashcards_workspace_id", "workspace_id"),
        Index("ix_flashcards_user_id", "user_id"),
        Index("ix_flashcards_document_id", "document_id"),
        Index("ix_flashcards_card_type", "card_type"),  # For filtering by card type (basic, cloze, qa, etc.)
        Index("ix_flashcards_workspace_user", "workspace_id", "user_id"),  # Composite for workspace + user queries
        Index("ix_flashcards_batch_id", "batch_id"),  # For filtering by generation batch
        Index("ix_flashcards_document_mode", "document_id", "card_type"),  # For duplicate detection (document + mode)
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
    card_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    front: Mapped[str | None] = mapped_column(Text, nullable=True)
    back: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_chunk_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )  # Chunk IDs used to generate this flashcard
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # Batch/generation ID to group cards from same generation run
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
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
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="flashcards"
    )
    user: Mapped["User"] = relationship("User", back_populates="flashcards")
    document: Mapped["Document | None"] = relationship(
        "Document", back_populates="flashcards"
    )
    reviews: Mapped[list["FlashcardReview"]] = relationship(
        "FlashcardReview", back_populates="flashcard", cascade="all, delete-orphan"
    )
    srs_states: Mapped[list["FlashcardSRSState"]] = relationship(
        "FlashcardSRSState", back_populates="flashcard", cascade="all, delete-orphan"
    )

