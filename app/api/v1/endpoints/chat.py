"""Chat endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.router import AgentRouter
from app.agents.types import StudyChatAgentInput, StudyChatAgentOutput
from app.api.dependencies import get_agent_router
from app.infrastructure.database import get_db
from app.schemas.chat import ChatResponse
from app.schemas.common import ErrorResponse
from app.services.conversation_service import ConversationService

router = APIRouter()


def get_request_id(x_request_id: Annotated[str | None, Header()] = None) -> str:
    """Extract or generate request ID."""
    import uuid as uuid_lib

    return x_request_id or str(uuid_lib.uuid4())


# Rate limit placeholder
async def check_rate_limit(
    workspace_id: uuid.UUID, user_id: uuid.UUID, request_id: str
) -> None:
    """Placeholder for rate limiting logic.
    
    TODO: Implement actual rate limiting (e.g., using slowapi or redis)
    """
    # Placeholder: no-op for now
    pass


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Chat with study assistant",
    description="Ask questions about documents in your workspace. Returns answer with citations (chunk_ids). Does not mutate state (no auto notes/flashcards/KG).",
)
async def chat(
    request: StudyChatAgentInput,
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)],
    request_id: Annotated[str, Depends(get_request_id)],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> ChatResponse:
    """Chat endpoint that uses StudyChatAgent.
    
    Behavior per contract:
    - Answers ONLY using retrieved chunks
    - Returns citations as chunk_ids used
    - If retrieval returns empty, responds with "I don't have enough context" message
    - Does NOT mutate state (no auto notes/flashcards/KG)
    - Supports conversation history for follow-up questions
    """
    # Rate limit check (placeholder)
    await check_rate_limit(request.workspace_id, request.user_id, request_id)

    try:
        # Handle conversation history
        conversation_id = request.conversation_id
        previous_messages = None
        
        if conversation_id:
            # Load previous messages from conversation
            conversation_service = ConversationService(db)
            conversation = await conversation_service.get_conversation(conversation_id)
            if conversation:
                messages = await conversation_service.get_conversation_messages(
                    conversation_id, limit=10  # Last 10 messages for context
                )
                previous_messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
            else:
                # Invalid conversation_id, ignore it
                conversation_id = None
        
        # Update request with previous messages if available
        if previous_messages:
            request.previous_messages = previous_messages
        
        # Run study chat agent (router provided via dependency)
        result: StudyChatAgentOutput = await agent_router.run_study_chat(request)
        
        # Store messages in conversation if conversation_id provided
        if conversation_id:
            conversation_service = ConversationService(db)
            # Store user message
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )
            # Store assistant response
            citations_data = [
                {
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                    "chunk_index": c.chunk_index,
                    "score": c.score,
                }
                for c in result.citations
            ]
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.answer,
                citations=citations_data,
                metadata={
                    "confidence_score": result.confidence_score,
                    "insufficient_info": result.insufficient_info,
                },
            )
        elif not conversation_id and request.conversation_id is None:
            # Create new conversation if not provided
            conversation_service = ConversationService(db)
            conversation = await conversation_service.create_conversation(
                workspace_id=request.workspace_id,
                user_id=request.user_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            )
            conversation_id = conversation.id
            # Store messages
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )
            citations_data = [
                {
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                    "chunk_index": c.chunk_index,
                    "score": c.score,
                }
                for c in result.citations
            ]
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.answer,
                citations=citations_data,
                metadata={
                    "confidence_score": result.confidence_score,
                    "insufficient_info": result.insufficient_info,
                },
            )

        # Convert to response format
        import uuid as uuid_lib
        message_id = uuid_lib.uuid4()

        # Build citations metadata (chunk_ids as per contract)
        citations_metadata = [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "chunk_index": c.chunk_index,
                "score": c.score,
            }
            for c in result.citations
        ]

        metadata = {
            "citations": citations_metadata,
            "request_id": request_id,
            "confidence_score": result.confidence_score,
            "insufficient_info": result.insufficient_info,
        }
        
        # Add conversation_id if created or used
        if conversation_id:
            metadata["conversation_id"] = str(conversation_id)

        # Optional suggested note (does not auto-create - deterministic)
        if result.suggested_note:
            metadata["suggested_note"] = {
                "title": result.suggested_note.title,
                "body": result.suggested_note.body,
                "document_id": str(result.suggested_note.document_id)
                if result.suggested_note.document_id
                else None,
            }

        # Get run_id from agent run if available
        run_id = None  # TODO: Extract from agent run logging

        return ChatResponse(
            message_id=message_id,
            content=result.answer,
            workspace_id=request.workspace_id,
            metadata=metadata,
            tokens_used=None,  # TODO: Extract from agent run if available
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log error with request ID
        import logging
        logger = logging.getLogger(__name__)
        error_str = str(e).lower()
        logger.error(f"Chat request failed [request_id={request_id}]: {str(e)}", exc_info=True)
        
        # Provide user-friendly error messages with "try again" guidance
        if "timeout" in error_str or "timed out" in error_str:
            error_msg = (
                f"Request timed out. Please try again with a shorter query or wait a moment. "
                f"[request_id={request_id}]"
            )
        elif "connection" in error_str or "unreachable" in error_str:
            error_msg = (
                f"Service temporarily unavailable. Please try again in a moment. "
                f"[request_id={request_id}]"
            )
        elif "rate limit" in error_str or "quota" in error_str:
            error_msg = (
                f"Rate limit exceeded. Please wait a moment before trying again. "
                f"[request_id={request_id}]"
            )
        else:
            error_msg = (
                f"An error occurred processing your request. Please try again in a moment. "
                f"If the problem persists, contact support. [request_id={request_id}]"
            )
        
        raise HTTPException(status_code=500, detail=error_msg)

