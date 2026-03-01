"""Chat and conversation history endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.study_chat_graph import STUDY_CHAT_ERROR_ANSWER
from app.agents.router import AgentRouter
from app.agents.types import StudyChatAgentInput, StudyChatAgentOutput
from app.api.dependencies import get_agent_router
from app.core.security import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.chat import ChatResponse
from app.schemas.common import ErrorResponse
from app.schemas.conversation import ConversationListItem, ConversationMessageRead
from app.services.conversation_service import ConversationService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


async def _check_workspace_access(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[Workspace | None, bool]:
    """Return (workspace, has_access)."""
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        return None, False
    if workspace.owner_id == user_id:
        return workspace, True
    mem_stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user_id,
    )
    mem_result = await db.execute(mem_stmt)
    return workspace, mem_result.scalar_one_or_none() is not None


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
    responses={
        401: {"description": "Missing or invalid JWT (send Authorization: Bearer <token>)"},
        403: {"description": "Not owner or member of the workspace"},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Chat with study assistant",
    description="Ask questions about documents in your workspace. Requires JWT and workspace access (owner or member). Retrieves chunks from Qdrant for the workspace and answers using only that context. Returns answer with citations (chunk_ids).",
)
async def chat(
    request: StudyChatAgentInput,
    current_user: Annotated[User, Depends(get_current_user)],
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
    # Override user_id from request with authenticated user
    request.user_id = current_user.id

    # Verify user has access to the workspace (owner or member)
    workspace_service = WorkspaceService(db)
    workspace = await workspace_service.get_workspace(request.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace {request.workspace_id} not found")
    is_owner = workspace.owner_id == current_user.id
    if not is_owner:
        from sqlalchemy import select
        from app.models.workspace_membership import WorkspaceMembership
        stmt = select(WorkspaceMembership).where(
            (WorkspaceMembership.workspace_id == request.workspace_id)
            & (WorkspaceMembership.user_id == current_user.id)
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to chat in this workspace",
            )

    # Rate limit check (placeholder)
    await check_rate_limit(request.workspace_id, current_user.id, request_id)

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
        
        # Don't persist the assistant message when the agent returned the generic error (so history stays clean)
        is_error_response = (
            result.answer.strip() == STUDY_CHAT_ERROR_ANSWER.strip()
            or result.answer.strip().startswith("I'm sorry, I encountered an error")
        )

        # Store messages in conversation if conversation_id provided
        if conversation_id:
            conversation_service = ConversationService(db)
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )
            if not is_error_response:
                citations_data = [
                    {"chunk_id": str(c.chunk_id), "document_id": str(c.document_id), "chunk_index": c.chunk_index, "score": c.score}
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
            conversation_service = ConversationService(db)
            conversation = await conversation_service.create_conversation(
                workspace_id=request.workspace_id,
                user_id=current_user.id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            )
            conversation_id = conversation.id
            await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )
            if not is_error_response:
                citations_data = [
                    {"chunk_id": str(c.chunk_id), "document_id": str(c.document_id), "chunk_index": c.chunk_index, "score": c.score}
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
        
        # Add conversation_id and full conversation history so the response includes all Q&A (no second GET needed)
        if conversation_id:
            metadata["conversation_id"] = str(conversation_id)
            conv_svc = ConversationService(db)
            all_messages = await conv_svc.get_conversation_messages(conversation_id)
            metadata["messages"] = [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "citations": getattr(m, "citations", None),
                    "metadata": getattr(m, "meta_data", None),
                    "created_at": m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
                }
                for m in all_messages
            ]

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


@router.get(
    "/workspaces/{workspace_id}/conversations",
    response_model=list[ConversationListItem] | list[ConversationMessageRead],
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="List conversations or all messages in a workspace",
    description="With include_messages=true (default): one query on conversation_messages (by workspace_id), returns flat list of all Q&A. With include_messages=false: returns conversation list only.",
)
async def list_workspace_conversations(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_messages: bool = True,
) -> list[ConversationListItem] | list[ConversationMessageRead]:
    """With include_messages: query only conversation_messages for this workspace (subquery on conversations), return flat list. Otherwise return conversation list."""
    workspace, has_access = await _check_workspace_access(db, workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workspace",
        )
    conversation_service = ConversationService(db)
    if not include_messages:
        conversations = await conversation_service.list_conversations(
            workspace_id=workspace_id,
            user_id=current_user.id,
            limit=50,
            offset=0,
        )
        return [ConversationListItem.model_validate(c) for c in conversations]
    # Single query: SELECT from conversation_messages WHERE conversation_id IN (SELECT id FROM conversations WHERE workspace_id = ?)
    all_messages = await conversation_service.get_all_messages_for_workspace(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    return [ConversationMessageRead.from_orm_message(m) for m in all_messages]
