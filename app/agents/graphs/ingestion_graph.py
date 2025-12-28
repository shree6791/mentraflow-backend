"""Centralized ingestion graph definition."""
import logging
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.types import IngestionAgentInput

logger = logging.getLogger(__name__)


class IngestionState(TypedDict):
    """State for ingestion agent graph."""

    input_data: IngestionAgentInput
    document_id: Any
    document: Any  # Document model
    chunks: list[Any]
    embeddings: list[Any]
    error: str | None
    status: Literal["pending", "storing", "chunking", "embedding", "completed", "failed"]
    service_tools: Any
    db: Any
    run_id: Any  # Agent run ID for logging steps


def build_ingestion_graph(service_tools: Any, db: Any) -> StateGraph:
    """Build the ingestion graph.
    
    Args:
        service_tools: ServiceTools instance
        db: Database session
        
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(IngestionState)

    # Add nodes
    workflow.add_node("validate_document", _validate_document)
    workflow.add_node("store_raw_text", _store_raw_text)
    workflow.add_node("chunk_document", _chunk_document)
    workflow.add_node("embed_chunks", _embed_chunks)
    workflow.add_node("generate_summary", _generate_summary)  # Optional: generate summary after ingest
    workflow.add_node("update_status", _update_status)
    workflow.add_node("handle_error", _handle_error)

    # Define edges
    workflow.set_entry_point("validate_document")
    workflow.add_edge("validate_document", "store_raw_text")
    workflow.add_conditional_edges(
        "store_raw_text",
        _should_continue_after_store,
        {
            "continue": "chunk_document",
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "chunk_document",
        _should_continue_after_chunk,
        {
            "continue": "embed_chunks",
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "embed_chunks",
        _should_continue_after_embed,
        {
            "continue": "generate_summary",
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "generate_summary",
        _should_continue_after_summary,
        {
            "continue": "update_status",
            "error": "update_status",  # Continue even if summary fails
        },
    )
    workflow.add_edge("update_status", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


async def _log_step(
    state: IngestionState,
    step_name: str,
    step_status: str,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Helper to log a step in the agent run.
    
    Args:
        state: Ingestion state
        step_name: Name of the step (e.g., "chunk", "embed", "upsert", "audit")
        step_status: Status of the step ("started", "completed", "failed", "skipped")
        details: Optional details about the step (e.g., count, duration)
        error: Optional error message if step failed
    """
    run_id = state.get("run_id")
    if not run_id:
        return
    
    try:
        from app.services.agent_run_service import AgentRunService
        agent_run_service = AgentRunService(state["db"])
        await agent_run_service.log_step(
            run_id=run_id,
            step_name=step_name,
            step_status=step_status,
            details=details,
            error=error,
        )
    except Exception as e:
        logger.warning(f"Failed to log step {step_name}: {str(e)}")


async def _validate_document(state: IngestionState) -> IngestionState:
    """Validate document exists."""
    await _log_step(state, "validate_document", "started")
    
    input_data = state["input_data"]
    service_tools = state["service_tools"]
    document = await service_tools.document_service.get_document(
        input_data.document_id
    )
    if not document:
        await _log_step(
            state,
            "validate_document",
            "failed",
            error=f"Document {input_data.document_id} not found",
        )
        return {
            **state,
            "error": f"Document {input_data.document_id} not found",
            "status": "failed",
        }
    
    await _log_step(
        state,
        "validate_document",
        "completed",
        details={"document_id": str(document.id), "title": document.title},
    )
    
    return {
        **state,
        "document_id": input_data.document_id,
        "document": document,
        "status": "pending",
    }


async def _store_raw_text(state: IngestionState) -> IngestionState:
    """Store raw text if provided."""
    await _log_step(state, "store_raw_text", "started")
    
    input_data = state["input_data"]
    document = state["document"]
    service_tools = state["service_tools"]

    try:
        if input_data.raw_text:
            await service_tools.document_service.store_raw_text(
                input_data.document_id, input_data.raw_text
            )
            await _log_step(
                state,
                "store_raw_text",
                "completed",
                details={"text_length": len(input_data.raw_text)},
            )
        elif not document.content:
            await _log_step(
                state,
                "store_raw_text",
                "failed",
                error="Document has no content and no raw_text provided",
            )
            return {
                **state,
                "error": f"Document {input_data.document_id} has no content and no raw_text provided",
                "status": "failed",
            }
        else:
            await _log_step(
                state,
                "store_raw_text",
                "completed",
                details={"source": "existing_content", "text_length": len(document.content) if document.content else 0},
            )
        return {**state, "status": "storing"}
    except Exception as e:
        await _log_step(state, "store_raw_text", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


async def _chunk_document(state: IngestionState) -> IngestionState:
    """Chunk the document."""
    await _log_step(state, "chunk", "started")
    
    service_tools = state["service_tools"]
    try:
        chunks = await service_tools.chunking_service.chunk_document(
            state["document_id"]
        )
        await _log_step(
            state,
            "chunk",
            "completed",
            details={"chunks_created": len(chunks)},
        )
        return {**state, "chunks": chunks, "status": "chunking"}
    except Exception as e:
        await _log_step(state, "chunk", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


async def _embed_chunks(state: IngestionState) -> IngestionState:
    """Embed the chunks and upsert to Qdrant."""
    await _log_step(state, "embed", "started")
    
    service_tools = state["service_tools"]
    try:
        embeddings = await service_tools.embedding_service.embed_chunks(
            state["document_id"]
        )
        await _log_step(
            state,
            "embed",
            "completed",
            details={"embeddings_created": len(embeddings)},
        )
        
        # Log Qdrant upsert step (upsert happens inside embed_chunks)
        if embeddings:
            await _log_step(state, "upsert", "started")
            # Note: upsert happens inside embed_chunks, so we log it here
            await _log_step(
                state,
                "upsert",
                "completed",
                details={"points_upserted": len(embeddings), "collection": "mentraflow_chunks"},
            )
        
        return {**state, "embeddings": embeddings, "status": "embedding"}
    except Exception as e:
        await _log_step(state, "embed", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


async def _generate_summary(state: IngestionState) -> IngestionState:
    """Generate summary after ingestion (best effort - failures don't block)."""
    input_data = state["input_data"]
    db = state["db"]
    
    try:
        # Check user preferences for auto_summary_after_ingest
        from app.services.user_preference_service import UserPreferenceService
        pref_service = UserPreferenceService(db)
        preferences = await pref_service.get_preferences(user_id=input_data.user_id)
        
        if preferences.auto_summary_after_ingest:
            await _log_step(state, "summary", "started")
            from app.services.summary_service import SummaryService
            summary_service = SummaryService(db)
            summary_text = await summary_service.generate_summary(
                document_id=input_data.document_id,
                max_bullets=7,
            )
            await summary_service.store_summary(
                document_id=input_data.document_id,
                summary_text=summary_text,
            )
            await _log_step(
                state,
                "summary",
                "completed",
                details={"summary_length": len(summary_text) if summary_text else 0},
            )
        else:
            await _log_step(
                state,
                "summary",
                "skipped",
                details={"reason": "auto_summary_after_ingest is false"},
            )
    except Exception as e:
        # Log but don't fail - summary is optional
        await _log_step(state, "summary", "failed", error=str(e))
        logger.warning(f"Summary generation failed for document {input_data.document_id}: {str(e)}")
    
    return state


async def _update_status(state: IngestionState) -> IngestionState:
    """Update document status to ready."""
    await _log_step(state, "audit", "started")
    
    document = state["document"]
    db = state["db"]
    
    # Refresh document to get latest state
    from sqlalchemy import select
    from app.models.document import Document
    stmt = select(Document).where(Document.id == state["document_id"])
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()
    
    if document:
        document.status = "ready"  # Use "ready" instead of "processed" per contract
        await db.commit()
        
        await _log_step(
            state,
            "audit",
            "completed",
            details={
                "document_status": "ready",
                "chunks_count": len(state.get("chunks", [])),
                "embeddings_count": len(state.get("embeddings", [])),
            },
        )
    
    return {**state, "status": "completed"}


async def _handle_error(state: IngestionState) -> IngestionState:
    """Handle errors in the workflow - update document status to failed."""
    document_id = state["document_id"]
    error = state.get("error", "Unknown error")
    db = state["db"]
    
    await _log_step(state, "error_handling", "started", error=error)
    
    try:
        # Update document status to failed
        from sqlalchemy import select
        from app.models.document import Document
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        
        if document:
            document.status = "failed"
            await db.commit()
            await _log_step(
                state,
                "error_handling",
                "completed",
                details={"document_status": "failed", "error": error},
            )
        else:
            await _log_step(
                state,
                "error_handling",
                "failed",
                error=f"Document {document_id} not found for status update",
            )
    except Exception as e:
        await _log_step(
            state,
            "error_handling",
            "failed",
            error=f"Failed to update document status: {str(e)}",
        )
        logger.error(f"Error updating document status to failed: {str(e)}", exc_info=True)
    
    return state


def _should_continue_after_store(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue after storing."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_chunk(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue after chunking."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_embed(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue after embedding."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_summary(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue after summary generation."""
    # Always continue - summary failures don't block ingestion
    return "continue"

