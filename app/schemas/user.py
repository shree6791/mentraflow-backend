"""User schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: EmailStr = Field(description="User email address")
    full_name: str | None = Field(default=None, description="User's full name")
    display_name: str | None = Field(default=None, description="User's display name")
    timezone: str | None = Field(default=None, description="User's timezone")
    learning_goal: str | None = Field(default=None, description="User's learning goal")
    experience_level: str | None = Field(default=None, description="User's experience level")
    preferred_language: str | None = Field(default=None, description="User's preferred language")
    bio: str | None = Field(default=None, description="User's biography")


class UserRead(BaseModel):
    """Schema for reading a user."""

    id: uuid.UUID = Field(description="User ID")
    email: str = Field(description="User email address")
    full_name: str | None = Field(default=None, description="User's full name")
    display_name: str | None = Field(default=None, description="User's display name")
    timezone: str | None = Field(default=None, description="User's timezone")
    learning_goal: str | None = Field(default=None, description="User's learning goal")
    experience_level: str | None = Field(default=None, description="User's experience level")
    preferred_language: str | None = Field(default=None, description="User's preferred language")
    bio: str | None = Field(default=None, description="User's biography")
    created_at: datetime = Field(description="User creation timestamp")
    updated_at: datetime = Field(description="User last update timestamp")

    model_config = ConfigDict(from_attributes=True)

