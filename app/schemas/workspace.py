"""Workspace schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace."""

    name: str = Field(description="Workspace name")
    plan_tier: str | None = Field(default=None, description="Subscription plan tier")


class WorkspaceRead(BaseModel):
    """Schema for reading a workspace."""

    id: uuid.UUID = Field(description="Workspace ID")
    name: str = Field(description="Workspace name")
    user_id: uuid.UUID = Field(description="Owner user ID", alias="owner_id")
    plan_tier: str | None = Field(default=None, description="Subscription plan tier")
    created_at: datetime = Field(description="Workspace creation timestamp")
    updated_at: datetime = Field(description="Workspace last update timestamp")

    model_config = ConfigDict(from_attributes=True)

