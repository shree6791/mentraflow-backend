"""User service."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_preference import UserPreference
from app.services.base import BaseService
from app.services.user_preference_service import get_default_preferences


class UserService(BaseService):
    """Service for user operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

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
        # Use single source of truth for default values
        preference = get_default_preferences(user.id)
        self.db.add(preference)
        
        await self._commit_and_refresh(user)
        return user

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
        
        await self._commit_and_refresh(user)
        return user

