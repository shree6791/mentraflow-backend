"""Preferences endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DEFAULT_AUTO_FLASHCARDS_AFTER_INGEST,
    DEFAULT_AUTO_INGEST_ON_UPLOAD,
    DEFAULT_AUTO_SUMMARY_AFTER_INGEST,
    DEFAULT_FLASHCARD_MODE,
)
from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse
from app.services.user_preference_service import UserPreferenceService

router = APIRouter()


class PreferenceRead(BaseModel):
    """Schema for reading preferences."""
    user_id: uuid.UUID = Field(description="User ID")
    auto_ingest_on_upload: bool | None = Field(
        default=DEFAULT_AUTO_INGEST_ON_UPLOAD, description="Auto-ingest on upload"
    )
    auto_summary_after_ingest: bool | None = Field(
        default=DEFAULT_AUTO_SUMMARY_AFTER_INGEST, description="Auto-summary after ingest"
    )
    auto_flashcards_after_ingest: bool | None = Field(
        default=DEFAULT_AUTO_FLASHCARDS_AFTER_INGEST, description="Auto-flashcards after ingest"
    )
    default_flashcard_mode: str | None = Field(
        default=DEFAULT_FLASHCARD_MODE, description="Default flashcard mode"
    )


class PreferenceUpdate(BaseModel):
    """Schema for updating preferences."""
    auto_ingest_on_upload: bool | None = Field(default=None)
    auto_summary_after_ingest: bool | None = Field(default=None)
    auto_flashcards_after_ingest: bool | None = Field(default=None)
    default_flashcard_mode: str | None = Field(default=None)


@router.get(
    "/preferences",
    response_model=PreferenceRead,
    responses={500: {"model": ErrorResponse}},
    summary="Get user preferences",
)
async def get_preferences(
    user_id: Annotated[uuid.UUID, Query(description="User ID")],
    workspace_id: Annotated[uuid.UUID | None, Query(description="Workspace ID (optional)")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PreferenceRead:
    """Get user preferences, creating defaults if not exists."""
    try:
        service = UserPreferenceService(db)
        preference = await service.get_preferences(user_id=user_id, workspace_id=workspace_id)
        return PreferenceRead(
            user_id=preference.user_id,
            auto_ingest_on_upload=preference.auto_ingest_on_upload,
            auto_summary_after_ingest=preference.auto_summary_after_ingest,
            auto_flashcards_after_ingest=preference.auto_flashcards_after_ingest,
            default_flashcard_mode=preference.default_flashcard_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting preferences: {str(e)}")


@router.patch(
    "/preferences",
    response_model=PreferenceRead,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update user preferences",
)
async def update_preferences(
    request: PreferenceUpdate,
    user_id: Annotated[uuid.UUID, Query(description="User ID")],
    workspace_id: Annotated[uuid.UUID | None, Query(description="Workspace ID (optional)")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PreferenceRead:
    """Update user preferences."""
    try:
        service = UserPreferenceService(db)
        preference = await service.update_preferences(
            user_id=user_id,
            auto_ingest_on_upload=request.auto_ingest_on_upload,
            auto_summary_after_ingest=request.auto_summary_after_ingest,
            auto_flashcards_after_ingest=request.auto_flashcards_after_ingest,
            default_flashcard_mode=request.default_flashcard_mode,
        )
        return PreferenceRead(
            user_id=preference.user_id,
            auto_ingest_on_upload=preference.auto_ingest_on_upload,
            auto_summary_after_ingest=preference.auto_summary_after_ingest,
            auto_flashcards_after_ingest=preference.auto_flashcards_after_ingest,
            default_flashcard_mode=preference.default_flashcard_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating preferences: {str(e)}")

