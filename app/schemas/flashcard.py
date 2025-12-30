"""Flashcard schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class FlashcardRead(BaseModel):
    """Schema for reading a flashcard."""

    id: uuid.UUID = Field(description="Flashcard ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    document_id: uuid.UUID | None = Field(default=None, description="Related document ID")
    card_type: str | None = Field(default=None, description="Flashcard type (qa, mcq, etc.)")
    front: str | None = Field(default=None, description="Front side content (question for qa/mcq)")
    back: str | None = Field(default=None, description="Back side content (answer for qa, correct answer letter for mcq)")
    tags: list[str] | None = Field(default=None, description="Flashcard tags")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata",
        alias="meta_data",  # Read from model's meta_data attribute
        serialization_alias="metadata",  # Serialize as metadata in API response
    )
    created_at: datetime = Field(description="Flashcard creation timestamp")
    updated_at: datetime = Field(description="Flashcard last update timestamp")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    # Convenience fields for MCQ cards (computed from metadata)
    @computed_field
    @property
    def options(self) -> list[str] | None:
        """MCQ options (A, B, C, D) - only present for mcq card_type.
        
        Example: ["Option A text", "Option B text", "Option C text", "Option D text"]
        """
        if self.card_type == "mcq" and self.metadata:
            return self.metadata.get("options")
        return None
    
    @computed_field
    @property
    def correct_answer(self) -> str | None:
        """MCQ correct answer letter (A, B, C, or D) - only present for mcq card_type.
        
        Example: "B" means the second option is correct.
        """
        if self.card_type == "mcq" and self.metadata:
            return self.metadata.get("correct_answer")
        return None


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

