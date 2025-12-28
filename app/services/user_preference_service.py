"""User preference service."""
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference


class UserPreferenceService:
    """Service for user preference operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

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
            # Create default preferences
            preference = UserPreference(
                user_id=user_id,
                auto_ingest_on_upload=True,
                auto_summary_after_ingest=True,
                auto_flashcards_after_ingest=False,
                default_flashcard_mode="qa",
            )
            self.db.add(preference)
            await self.db.commit()
            await self.db.refresh(preference)
        
        return preference

    async def update_preferences(
        self,
        user_id: uuid.UUID,
        auto_ingest_on_upload: bool | None = None,
        auto_summary_after_ingest: bool | None = None,
        auto_flashcards_after_ingest: bool | None = None,
        default_flashcard_mode: str | None = None,
    ) -> UserPreference:
        """Update user preferences."""
        preference = await self.get_preferences(user_id)
        
        try:
            if auto_ingest_on_upload is not None:
                preference.auto_ingest_on_upload = auto_ingest_on_upload
            if auto_summary_after_ingest is not None:
                preference.auto_summary_after_ingest = auto_summary_after_ingest
            if auto_flashcards_after_ingest is not None:
                preference.auto_flashcards_after_ingest = auto_flashcards_after_ingest
            if default_flashcard_mode is not None:
                preference.default_flashcard_mode = default_flashcard_mode
            
            await self.db.commit()
            await self.db.refresh(preference)
            return preference
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while updating preferences: {str(e)}") from e

