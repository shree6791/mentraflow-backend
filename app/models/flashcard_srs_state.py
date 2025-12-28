"""Flashcard SRS state model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Float, Index, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.flashcard import Flashcard
    from app.models.user import User


class FlashcardSRSState(Base):
    """Flashcard spaced repetition system state model."""

    __tablename__ = "flashcard_srs_state"
    __table_args__ = (
        Index("ix_flashcard_srs_state_flashcard_id", "flashcard_id"),
        Index("ix_flashcard_srs_state_user_id", "user_id"),
        Index("ix_flashcard_srs_state_due_at", "due_at"),  # For date range queries in get_due_flashcards
        Index("ix_flashcard_srs_state_user_due", "user_id", "due_at"),  # Composite index for get_due_flashcards query pattern
    )

    flashcard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ease_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    repetitions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lapses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    flashcard: Mapped["Flashcard"] = relationship(
        "Flashcard", back_populates="srs_states"
    )
    user: Mapped["User"] = relationship("User", back_populates="flashcard_srs_states")

