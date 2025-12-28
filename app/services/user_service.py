"""User service."""
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_preference import UserPreference


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_user(
        self,
        username: str,
        email: str,
        full_name: str | None = None,
        display_name: str | None = None,
        auth_provider: str | None = None,  # "google", "email", etc.
        auth_provider_id: str | None = None,  # Google user ID, etc.
    ) -> User:
        """Create a new user and automatically create default preferences.
        
        When a user is created (via signup/login), default user preferences
        are automatically created proactively (not lazily).
        
        Args:
            username: Username (unique, required)
            email: User email (unique, required)
            full_name: Full name (optional)
            display_name: Display name (optional)
            auth_provider: Authentication provider ("google", "email", etc.)
            auth_provider_id: Provider-specific user ID (e.g., Google user ID)
            
        Returns:
            Created user with preferences already set
            
        Raises:
            ValueError: If username or email already exists or other validation error
        """
        try:
            # Check if user already exists by username
            stmt = select(User).where(User.username == username)
            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValueError(f"User with username {username} already exists")
            
            # Check if email already exists
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValueError(f"User with email {email} already exists")
            
            # Create user
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name or full_name,
            )
            self.db.add(user)
            await self.db.flush()  # Flush to get user.id before commit
            
            # Automatically create default preferences (PROACTIVE, not lazy)
            preference = UserPreference(
                user_id=user.id,
                auto_ingest_on_upload=True,
                auto_summary_after_ingest=True,
                auto_flashcards_after_ingest=False,
                default_flashcard_mode="qa",
            )
            self.db.add(preference)
            
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while creating user: {str(e)}") from e

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: uuid.UUID,
        full_name: str | None = None,
        display_name: str | None = None,
        timezone: str | None = None,
        learning_goal: str | None = None,
        experience_level: str | None = None,
        preferred_language: str | None = None,
        bio: str | None = None,
    ) -> User:
        """Update user information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        try:
            if full_name is not None:
                user.full_name = full_name
            if display_name is not None:
                user.display_name = display_name
            if timezone is not None:
                user.timezone = timezone
            if learning_goal is not None:
                user.learning_goal = learning_goal
            if experience_level is not None:
                user.experience_level = experience_level
            if preferred_language is not None:
                user.preferred_language = preferred_language
            if bio is not None:
                user.bio = bio
            
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while updating user: {str(e)}") from e

