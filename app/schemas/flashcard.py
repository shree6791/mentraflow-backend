"""Flashcard schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlashcardRead(BaseModel):
    """Schema for reading a flashcard."""

    id: uuid.UUID = Field(description="Flashcard ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    document_id: uuid.UUID | None = Field(default=None, description="Related document ID")
    card_type: str | None = Field(default=None, description="Flashcard type")
    front: str | None = Field(default=None, description="Front side content")
    back: str | None = Field(default=None, description="Back side content")
    tags: list[str] | None = Field(default=None, description="Flashcard tags")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(description="Flashcard creation timestamp")
    updated_at: datetime = Field(description="Flashcard last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class FlashcardReviewInput(BaseModel):
    """Schema for submitting a flashcard review."""

    flashcard_id: uuid.UUID = Field(description="Flashcard ID")
    rating: int = Field(ge=0, le=4, description="User rating (0-4): 0=Again, 1=Hard, 2=Good, 3=Easy, 4=Perfect")
    response_time_ms: int | None = Field(default=None, ge=0, description="Response time in milliseconds")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional review metadata")


class FlashcardReviewResponse(BaseModel):
    """Response after submitting a flashcard review."""

    review_id: uuid.UUID = Field(description="Review ID")
    flashcard_id: uuid.UUID = Field(description="Flashcard ID")
    next_review_due: datetime | None = Field(default=None, description="Next review due date")
    interval_days: int | None = Field(default=None, description="Current interval in days")
    ease_factor: float | None = Field(default=None, description="Ease factor")
    reviewed_at: datetime = Field(description="Review timestamp")

    model_config = ConfigDict(from_attributes=True)

