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
    workflow.add_node("generate_optional_content", _generate_optional_content)  # Parallel: summary, flashcards, KG
    workflow.add_node("update_status", _update_status)
    workflow.add_node("handle_error", _handle_error)

    # Define workflow edges (linear flow with error handling)
    workflow.set_entry_point("validate_document")
    workflow.add_edge("validate_document", "store_raw_text")
    
    # Each step can either continue or go to error handler
    workflow.add_conditional_edges(
        "store_raw_text",
        _should_continue,
        {"continue": "chunk_document", "error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "chunk_document",
        _should_continue,
        {"continue": "embed_chunks", "error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "embed_chunks",
        _should_continue,
        {"continue": "generate_optional_content", "error": "handle_error"},
    )
    
    # Optional content generation (summary, flashcards, KG) - always continue even on failure
    workflow.add_conditional_edges(
        "generate_optional_content",
        _should_continue_after_summary,  # Always continue - failures don't block
        {"continue": "update_status", "error": "update_status"},
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


async def _execute_step(
    state: IngestionState,
    step_name: str,
    operation: Any,
    on_success: Any,
    get_details: Any | None = None,
) -> IngestionState:
    """Execute a step with standardized error handling and logging.
    
    Args:
        state: Current ingestion state
        step_name: Name of the step for logging
        operation: Async callable that performs the operation
        on_success: Callable that takes result and returns updated state
        get_details: Optional callable to extract details from result for logging
        
    Returns:
        Updated state (with error set if operation failed)
    """
    await _log_step(state, step_name, "started")
    
    try:
        result = await operation()
        details = get_details(result) if get_details else None
        await _log_step(state, step_name, "completed", details=details)
        return on_success(result)
    except Exception as e:
        await _log_step(state, step_name, "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


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
    return await _execute_step(
        state,
        step_name="chunk",
        operation=lambda: state["service_tools"].chunking_service.chunk_document(
            state["document_id"]
        ),
        on_success=lambda chunks: {
            **state,
            "chunks": chunks,
            "status": "chunking",
        },
        get_details=lambda chunks: {"chunks_created": len(chunks)},
    )


async def _embed_chunks(state: IngestionState) -> IngestionState:
    """Embed the chunks and upsert to Qdrant."""
    result = await _execute_step(
        state,
        step_name="embed",
        operation=lambda: state["service_tools"].embedding_service.embed_chunks(
            state["document_id"]
        ),
        on_success=lambda embeddings: {
            **state,
            "embeddings": embeddings,
            "status": "embedding",
        },
        get_details=lambda embeddings: {"embeddings_created": len(embeddings)},
    )
    
    # Log Qdrant upsert (happens inside embed_chunks)
    if not result.get("error") and result.get("embeddings"):
        embeddings = result["embeddings"]
        await _log_step(state, "upsert", "started")
        await _log_step(
            state,
            "upsert",
            "completed",
            details={
                "points_upserted": len(embeddings),
                "collection": "mentraflow_chunks",
            },
        )
    
    return result


async def _generate_optional_content(state: IngestionState) -> IngestionState:
    """Generate summary, flashcards, and KG in parallel (best effort - failures don't block)."""
    import asyncio
    
    # Run all three operations in parallel
    # Each function handles its own errors internally, but we log any unexpected exceptions
    results = await asyncio.gather(
        _generate_summary(state),
        _generate_flashcards(state),
        _generate_kg(state),
        return_exceptions=True,  # Don't raise exceptions, let each function handle them
    )
    
    # Log any unexpected exceptions (shouldn't happen since each function handles errors)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            operation = ["summary", "flashcards", "kg"][i]
            logger.warning(f"Unexpected exception in {operation} generation: {str(result)}", exc_info=result)
    
    return state


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
            # Use SummaryAgent for consistency with other LLM operations
            from app.agents.summary_agent import SummaryAgent
            from app.agents.types import SummaryAgentInput
            
            summary_agent = SummaryAgent(db)
            from app.core.constants import DEFAULT_SUMMARY_MAX_BULLETS
            summary_input = SummaryAgentInput(
                document_id=input_data.document_id,
                workspace_id=input_data.workspace_id,
                user_id=input_data.user_id,
                max_bullets=DEFAULT_SUMMARY_MAX_BULLETS,
            )
            # Run without logging (already logged in ingestion graph)
            try:
                summary_output = await summary_agent.run_without_logging(summary_input)
                # Verify summary was actually generated
                if not summary_output or not summary_output.summary:
                    raise ValueError("Summary agent returned empty summary")
                
                # Verify summary was stored in database
                from sqlalchemy import select
                from app.models.document import Document
                stmt = select(Document).where(Document.id == input_data.document_id)
                result = await db.execute(stmt)
                document = result.scalar_one_or_none()
                if document and document.summary_text:
                    await _log_step(
                        state,
                        "summary",
                        "completed",
                        details={
                            "summary_length": summary_output.summary_length,
                            "stored_in_db": True,
                        },
                    )
                else:
                    # Summary was generated but not stored - this shouldn't happen
                    await _log_step(
                        state,
                        "summary",
                        "warning",
                        details={
                            "summary_length": summary_output.summary_length,
                            "stored_in_db": False,
                            "warning": "Summary generated but not found in database",
                        },
                    )
            except Exception as summary_error:
                # Re-raise to be caught by outer try/except
                raise
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
    
    return state


async def _generate_flashcards(state: IngestionState) -> IngestionState:
    """Generate flashcards after ingestion (best effort - failures don't block)."""
    input_data = state["input_data"]
    db = state["db"]
    
    try:
        # Check user preferences for auto_flashcards_after_ingest
        from app.services.user_preference_service import UserPreferenceService
        pref_service = UserPreferenceService(db)
        preferences = await pref_service.get_preferences(user_id=input_data.user_id)
        
        if preferences.auto_flashcards_after_ingest:
            await _log_step(state, "flashcards", "started")
            # Use FlashcardAgent for consistency with other LLM operations
            from app.agents.flashcard_agent import FlashcardAgent
            from app.agents.types import FlashcardAgentInput
            
            flashcard_agent = FlashcardAgent(db)
            # Use default_flashcard_mode from preferences, fallback to constant
            from app.core.constants import DEFAULT_FLASHCARD_MODE
            flashcard_mode = preferences.default_flashcard_mode or DEFAULT_FLASHCARD_MODE
            flashcard_input = FlashcardAgentInput(
                workspace_id=input_data.workspace_id,
                user_id=input_data.user_id,
                source_document_id=input_data.document_id,
                mode=flashcard_mode,
            )
            # Run without logging (already logged in ingestion graph)
            try:
                flashcard_output = await flashcard_agent.run_without_logging(flashcard_input)
                
                # Verify flashcards were actually created
                if not flashcard_output:
                    raise ValueError("Flashcard agent returned empty output")
                
                # Ensure any pending commits are flushed before querying
                await db.flush()
                
                # Verify flashcards were stored in database
                from sqlalchemy import select
                from app.models.flashcard import Flashcard
                stmt = select(Flashcard).where(
                    Flashcard.document_id == input_data.document_id,
                    Flashcard.workspace_id == input_data.workspace_id,
                )
                result = await db.execute(stmt)
                flashcards_in_db = result.scalars().all()
                
                if flashcard_output.flashcards_created > 0:
                    if len(flashcards_in_db) > 0:
                        await _log_step(
                            state,
                            "flashcards",
                            "completed",
                            details={
                                "flashcards_created": flashcard_output.flashcards_created,
                                "flashcards_in_db": len(flashcards_in_db),
                                "mode": flashcard_mode,
                                "dropped_count": flashcard_output.dropped_count,
                                "stored_in_db": True,
                            },
                        )
                    else:
                        # Flashcards were created but not found in database
                        await _log_step(
                            state,
                            "flashcards",
                            "warning",
                            details={
                                "flashcards_created": flashcard_output.flashcards_created,
                                "flashcards_in_db": len(flashcards_in_db),
                                "mode": flashcard_mode,
                                "dropped_count": flashcard_output.dropped_count,
                                "stored_in_db": False,
                                "warning": "Flashcards generated but not found in database",
                            },
                        )
                else:
                    # No flashcards created (might be due to insufficient content or validation)
                    await _log_step(
                        state,
                        "flashcards",
                        "completed",
                        details={
                            "flashcards_created": 0,
                            "reason": flashcard_output.reason or "unknown",
                            "mode": flashcard_mode,
                            "dropped_count": flashcard_output.dropped_count,
                        },
                    )
            except Exception as flashcard_error:
                # Re-raise to be caught by outer try/except
                raise
        else:
            await _log_step(
                state,
                "flashcards",
                "skipped",
                details={"reason": "auto_flashcards_after_ingest is false"},
            )
    except Exception as e:
        # Log but don't fail - flashcard generation is optional
        logger.error(f"Flashcard generation failed for document {input_data.document_id}: {str(e)}", exc_info=True)
        await _log_step(state, "flashcards", "failed", error=str(e))
    
    return state


async def _generate_kg(state: IngestionState) -> IngestionState:
    """Generate knowledge graph after ingestion (best effort - failures don't block)."""
    input_data = state["input_data"]
    db = state["db"]
    
    try:
        # Check user preferences for auto_kg_after_ingest
        from app.services.user_preference_service import UserPreferenceService
        pref_service = UserPreferenceService(db)
        preferences = await pref_service.get_preferences(user_id=input_data.user_id)
        
        if preferences.auto_kg_after_ingest:
            await _log_step(state, "kg_extraction", "started")
            # Use KGExtractionAgent for consistency with other LLM operations
            from app.agents.kg_extraction_agent import KGExtractionAgent
            from app.agents.types import KGExtractionAgentInput
            
            kg_agent = KGExtractionAgent(db)
            kg_input = KGExtractionAgentInput(
                workspace_id=input_data.workspace_id,
                user_id=input_data.user_id,
                source_document_id=input_data.document_id,
            )
            # Run without logging (already logged in ingestion graph)
            try:
                kg_output = await kg_agent.run_without_logging(kg_input)
                # Verify KG was actually extracted
                if not kg_output:
                    raise ValueError("KG extraction agent returned empty output")
                
                # Verify concepts and edges were stored in database
                from sqlalchemy import select
                from app.models.concept import Concept
                from app.models.kg_edge import KGEdge
                
                # Check concepts
                stmt = select(Concept).where(
                    Concept.workspace_id == input_data.workspace_id
                )
                result = await db.execute(stmt)
                concepts_in_db = result.scalars().all()
                
                # Check edges
                stmt = select(KGEdge).where(
                    KGEdge.workspace_id == input_data.workspace_id
                )
                result = await db.execute(stmt)
                edges_in_db = result.scalars().all()
                
                if kg_output.concepts_written > 0 or kg_output.edges_written > 0:
                    await _log_step(
                        state,
                        "kg_extraction",
                        "completed",
                        details={
                            "concepts_written": kg_output.concepts_written,
                            "edges_written": kg_output.edges_written,
                            "concepts_in_db": len(concepts_in_db),
                            "edges_in_db": len(edges_in_db),
                            "stored_in_db": True,
                        },
                    )
                else:
                    # No concepts/edges extracted (might be due to insufficient content)
                    await _log_step(
                        state,
                        "kg_extraction",
                        "completed",
                        details={
                            "concepts_written": 0,
                            "edges_written": 0,
                            "reason": "no_extractable_content",
                        },
                    )
            except Exception as kg_error:
                # Re-raise to be caught by outer try/except
                raise
        else:
            await _log_step(
                state,
                "kg_extraction",
                "skipped",
                details={"reason": "auto_kg_after_ingest is false"},
            )
    except Exception as e:
        # Log but don't fail - KG extraction is optional
        await _log_step(state, "kg_extraction", "failed", error=str(e))
    
    return state


async def _update_status(state: IngestionState) -> IngestionState:
    """Update document status to ready."""
    await _log_step(state, "audit", "started")
    
    db = state["db"]
    document_id = state["document_id"]
    
    try:
        from sqlalchemy import select
        from app.models.document import Document
        
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        
        if document:
            document.status = "ready"
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
    except Exception as e:
        await _log_step(state, "audit", "failed", error=str(e))
    
    return {**state, "status": "completed"}


async def _handle_error(state: IngestionState) -> IngestionState:
    """Handle errors in the workflow - update document status to failed."""
    document_id = state["document_id"]
    error = state.get("error", "Unknown error")
    db = state["db"]
    
    await _log_step(state, "error_handling", "started", error=error)
    
    try:
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
    
    return state


def _should_continue(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue to next step or handle error."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_summary(state: IngestionState) -> Literal["continue", "error"]:
    """Check if we should continue after summary generation."""
    # Always continue - summary failures don't block ingestion
    return "continue"

