"""Conversation and message schemas."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.conversation import ConversationMessage


class ConversationListItem(BaseModel):
    """Conversation summary for list-by-workspace API."""

    id: uuid.UUID = Field(description="Conversation ID")
    title: str | None = Field(default=None, description="Conversation title (e.g. first message snippet)")
    created_at: datetime = Field(description="When the conversation was created")
    updated_at: datetime = Field(description="When the conversation was last updated")

    model_config = {"from_attributes": True}


class ConversationWithMessages(ConversationListItem):
    """Conversation with full message history (for refresh / single-call load)."""

    messages: list["ConversationMessageRead"] = Field(default_factory=list, description="All messages in ascending order")


class ConversationMessageRead(BaseModel):
    """A single message in a conversation (for history API)."""

    id: uuid.UUID = Field(description="Message ID")
    conversation_id: uuid.UUID = Field(description="Conversation ID")
    role: str = Field(description="Message role: user or assistant")
    content: str = Field(description="Message content")
    citations: list[dict[str, Any]] | None = Field(default=None, description="Citations for assistant messages")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata (e.g. confidence_score)")
    created_at: datetime = Field(description="When the message was created")

    @classmethod
    def from_orm_message(cls, m: "ConversationMessage") -> "ConversationMessageRead":
        """Build from ConversationMessage ORM (meta_data -> metadata)."""
        return cls(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            metadata=getattr(m, "meta_data", None),
            created_at=m.created_at,
        )
