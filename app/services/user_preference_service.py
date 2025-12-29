"""User preference service."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DEFAULT_AUTO_FLASHCARDS_AFTER_INGEST,
    DEFAULT_AUTO_INGEST_ON_UPLOAD,
    DEFAULT_AUTO_KG_AFTER_INGEST,
    DEFAULT_AUTO_SUMMARY_AFTER_INGEST,
    DEFAULT_FLASHCARD_MODE,
)
from app.models.user_preference import UserPreference
from app.services.base import BaseService


def get_default_preferences(user_id: uuid.UUID) -> UserPreference:
    """Create a UserPreference instance with default values.
    
    This is the single source of truth for default user preferences.
    Used by both UserService (during user creation) and UserPreferenceService
    (when creating preferences for existing users).
    
    Args:
        user_id: User ID for the preferences
        
    Returns:
        UserPreference instance with default values
    """
    return UserPreference(
        user_id=user_id,
        auto_ingest_on_upload=DEFAULT_AUTO_INGEST_ON_UPLOAD,
        auto_summary_after_ingest=DEFAULT_AUTO_SUMMARY_AFTER_INGEST,
        auto_flashcards_after_ingest=DEFAULT_AUTO_FLASHCARDS_AFTER_INGEST,
        auto_kg_after_ingest=DEFAULT_AUTO_KG_AFTER_INGEST,
        default_flashcard_mode=DEFAULT_FLASHCARD_MODE,
    )


class UserPreferenceService(BaseService):
    """Service for user preference operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def get_preferences(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None = None,
    ) -> UserPreference:
        """Get user preferences, creating defaults if not exists."""
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.db.execute(stmt)
        preference = result.scalar_one_or_none()
        
        if not preference:
            # Create default preferences using single source of truth
            preference = get_default_preferences(user_id)
            self.db.add(preference)
            await self._commit_and_refresh(preference)
        
        return preference

    async def update_preferences(
        self,
        user_id: uuid.UUID,
        auto_ingest_on_upload: bool | None = None,
        auto_summary_after_ingest: bool | None = None,
        auto_flashcards_after_ingest: bool | None = None,
        auto_kg_after_ingest: bool | None = None,
        default_flashcard_mode: str | None = None,
    ) -> UserPreference:
        """Update user preferences."""
        preference = await self.get_preferences(user_id)
        
        if auto_ingest_on_upload is not None:
            preference.auto_ingest_on_upload = auto_ingest_on_upload
        if auto_summary_after_ingest is not None:
            preference.auto_summary_after_ingest = auto_summary_after_ingest
        if auto_flashcards_after_ingest is not None:
            preference.auto_flashcards_after_ingest = auto_flashcards_after_ingest
        if auto_kg_after_ingest is not None:
            preference.auto_kg_after_ingest = auto_kg_after_ingest
        if default_flashcard_mode is not None:
            preference.default_flashcard_mode = default_flashcard_mode
        
        await self._commit_and_refresh(preference)
        return preference

