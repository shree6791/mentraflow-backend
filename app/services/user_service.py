"""User service."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
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
        password: str | None = None,  # Plain text password (will be hashed)
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
        
        # Hash password if provided
        hashed_password_value = None
        if password:
            hashed_password_value = hash_password(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password_value,
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
    
    async def verify_user_password(self, email: str, password: str) -> User | None:
        """Verify user password and return user if valid.
        
        Args:
            email: User email
            password: Plain text password to verify
            
        Returns:
            User object if password is valid, None otherwise
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        # If user has no password (e.g., Google OAuth user), reject
        if not user.hashed_password:
            return None
        
        if verify_password(password, user.hashed_password):
            return user
        
        return None

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
    
    async def set_password_reset_token(self, email: str, token: str, expires_at) -> User:
        """Set password reset token for a user.
        
        Args:
            email: User email
            token: Reset token (JWT)
            expires_at: Token expiration datetime
            
        Returns:
            User object
            
        Raises:
            ValueError: If user not found
        """
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError(f"User with email {email} not found")
        
        user.password_reset_token = token
        user.password_reset_expires = expires_at
        await self._commit_and_refresh(user)
        return user
    
    async def reset_password_with_token(self, token: str, new_password: str) -> User:
        """Reset user password using reset token.
        
        Args:
            token: Password reset token
            new_password: New plain text password (will be hashed)
            
        Returns:
            User object
            
        Raises:
            ValueError: If token is invalid or expired
        """
        from datetime import datetime, timezone
        
        # Find user by reset token
        stmt = select(User).where(User.password_reset_token == token)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Invalid or expired reset token")
        
        # Check if token is expired
        if not user.password_reset_expires or user.password_reset_expires < datetime.now(timezone.utc):
            raise ValueError("Reset token has expired")
        
        # Hash new password
        hashed_password = hash_password(new_password)
        
        # Update password and clear reset token
        user.hashed_password = hashed_password
        user.password_reset_token = None
        user.password_reset_expires = None
        
        await self._commit_and_refresh(user)
        return user

