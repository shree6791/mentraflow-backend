"""User preference model."""
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Time, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(Base):
    """User preference model."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    daily_target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_study_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminders_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    difficulty_adaptive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gamification_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # MentraFlow v1 preferences
    auto_ingest_on_upload: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    auto_summary_after_ingest: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    auto_flashcards_after_ingest: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    default_flashcard_mode: Mapped[str | None] = mapped_column(Text, nullable=True, default="qa")
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
    user: Mapped["User"] = relationship("User", back_populates="preference")

