"""Conversation service for managing chat conversations."""
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage


class ConversationService:
    """Service for conversation operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_conversation(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        try:
            conversation = Conversation(
                workspace_id=workspace_id,
                user_id=user_id,
                title=title,
                metadata=metadata,
            )
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
            return conversation
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while creating conversation: {str(e)}") from e

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
        try:
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
                from sqlalchemy import func
                conversation.updated_at = func.now()
            
            await self.db.commit()
            await self.db.refresh(message)
            return message
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while adding message: {str(e)}") from e

    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        """Get messages for a conversation."""
        stmt = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        """Delete a conversation (cascade deletes messages)."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        try:
            await self.db.delete(conversation)
            await self.db.commit()
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while deleting conversation: {str(e)}") from e

