"""Conversation service for managing chat conversations."""
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage
from app.services.base import BaseService


class ConversationService(BaseService):
    """Service for conversation operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_conversation(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title,
            metadata=metadata,
        )
        self.db.add(conversation)
        await self._commit_and_refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Get a conversation by ID."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations in a workspace."""
        stmt = select(Conversation).where(Conversation.workspace_id == workspace_id)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        stmt = stmt.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        """Add a message to a conversation."""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
            metadata=metadata,
        )
        self.db.add(message)
        
        # Update conversation's updated_at timestamp
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.updated_at = func.now()
        
        await self._commit_and_refresh(message)
        return message

    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        """Get messages for a conversation."""
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_messages_for_workspace(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        only_valid_pairs: bool = True,
    ) -> list[ConversationMessage]:
        """Query only conversation_messages; filter by workspace via subquery. When only_valid_pairs=True, return messages only from conversations that have at least one assistant reply (valid Q&A pair)."""
        convos_in_workspace = select(Conversation.id).where(Conversation.workspace_id == workspace_id)
        if user_id is not None:
            convos_in_workspace = convos_in_workspace.where(Conversation.user_id == user_id)
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id.in_(convos_in_workspace))
        )
        if only_valid_pairs:
            convos_with_answer = (
                select(ConversationMessage.conversation_id)
                .where(ConversationMessage.role == "assistant")
                .distinct()
            )
            stmt = stmt.where(ConversationMessage.conversation_id.in_(convos_with_answer))
        stmt = stmt.order_by(
            ConversationMessage.conversation_id,
            ConversationMessage.created_at.asc(),
            ConversationMessage.id.asc(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        """Delete a conversation (cascade deletes messages)."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        await self.db.delete(conversation)
        await self.db.commit()

