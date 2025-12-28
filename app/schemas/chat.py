"""Chat schemas."""
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Individual chat message."""

    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Schema for chat request."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    messages: list[ChatMessage] = Field(description="Chat message history")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")
    stream: bool = Field(default=False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Schema for chat response."""

    message_id: uuid.UUID = Field(description="Generated message ID")
    content: str = Field(description="Response content")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    metadata: dict[str, Any] | None = Field(default=None, description="Response metadata")
    tokens_used: int | None = Field(default=None, description="Number of tokens used")

    model_config = ConfigDict(from_attributes=True)


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunk."""

    content: str = Field(description="Chunk content")
    done: bool = Field(default=False, description="Whether this is the final chunk")

