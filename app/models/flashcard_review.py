"""Flashcard review model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.flashcard import Flashcard
    from app.models.user import User


class FlashcardReview(Base):
    """Flashcard review model."""

    __tablename__ = "flashcard_reviews"
    __table_args__ = (
        Index("ix_flashcard_reviews_flashcard_id", "flashcard_id"),
        Index("ix_flashcard_reviews_user_id", "user_id"),
        Index("ix_flashcard_reviews_reviewed_at", "reviewed_at"),  # For time-based analytics queries
        Index("ix_flashcard_reviews_user_reviewed", "user_id", "reviewed_at"),  # Composite for user review history
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    flashcard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, name="metadata")

    # Relationships
    flashcard: Mapped["Flashcard"] = relationship(
        "Flashcard", back_populates="reviews"
    )
    user: Mapped["User"] = relationship("User", back_populates="flashcard_reviews")

