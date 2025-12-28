"""LangGraph workflow for document summary generation."""
import logging
import uuid
from typing import Any, Literal, TypedDict

from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel, Field
from langgraph.graph import END, StateGraph

from app.agents.types import SummaryAgentInput

logger = logging.getLogger(__name__)


class SummaryResponse(LangChainBaseModel):
    """Structured response from LLM for summary generation."""

    summary: str = Field(description="Generated summary text in bullet points or paragraph format")


class SummaryState(TypedDict):
    """State for summary agent graph."""

    input_data: SummaryAgentInput
    document: Any  # Document model
    search_results: list[dict]  # Retrieved chunks from semantic search
    quality_metrics: dict[str, Any]  # Content quality analysis
    combined_text: str  # Combined chunk text for LLM
    llm_response: SummaryResponse | None  # LLM structured output
    summary: str | None  # Final summary text
    error: str | None
    status: Literal[
        "pending",
        "retrieving",
        "analyzing_quality",
        "generating",
        "storing",
        "completed",
        "failed",
    ]
    service_tools: Any
    llm: Any
    system_prompt: str
    db: Any


async def _log_step(
    state: SummaryState,
    step_name: str,
    step_status: str,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Helper to log a step in the agent run."""
    # This could be enhanced to write to agent_runs.steps JSONB field
    log_msg = f"Summary step '{step_name}': {step_status}"
    if details:
        log_msg += f" | Details: {details}"
    if error:
        log_msg += f" | Error: {error}"
    logger.info(log_msg)


async def _retrieve_chunks(state: SummaryState) -> SummaryState:
    """Retrieve relevant chunks using semantic search."""
    input_data = state["input_data"]
    service_tools = state["service_tools"]
    db = state["db"]

    try:
        await _log_step(state, "retrieve_chunks", "started")

        # Get document
        document = await service_tools.document_service.get_document(input_data.document_id)
        if not document:
            raise ValueError(f"Document {input_data.document_id} not found")

        workspace_id = document.workspace_id

        # Use semantic retrieval to find most important chunks
        # Search for key concepts and main ideas
        summary_queries = [
            "key concepts main ideas important points",
            "summary overview main themes",
            "core principles central arguments",
        ]

        all_retrieved_chunks = []
        seen_chunk_ids = set()

        # Retrieve chunks using multiple semantic queries for diversity
        for query in summary_queries:
            search_results = await service_tools.retrieval_service.semantic_search(
                workspace_id=workspace_id,
                query=query,
                top_k=5,  # Get top 5 for each query
                filters={"document_id": str(input_data.document_id)},
            )

            # Add unique chunks (avoid duplicates)
            for result in search_results:
                chunk_id = result.get("chunk_id")
                if chunk_id and chunk_id not in seen_chunk_ids:
                    all_retrieved_chunks.append(result)
                    seen_chunk_ids.add(chunk_id)

        # If semantic retrieval didn't work (e.g., embeddings not ready), fallback to first chunks
        if not all_retrieved_chunks:
            logger.warning(
                f"Semantic retrieval returned no results for document {input_data.document_id}, using first chunks as fallback"
            )
            from app.models.document_chunk import DocumentChunk
            from sqlalchemy import select

            stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.document_id == input_data.document_id)
                .order_by(DocumentChunk.chunk_index)
                .limit(8)
            )
            result = await db.execute(stmt)
            chunks = list(result.scalars().all())

            all_retrieved_chunks = [
                {
                    "chunk_id": str(chunk.id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "score": 1.0,  # Default score for fallback
                }
                for chunk in chunks
                if chunk.content
            ]

        if not all_retrieved_chunks:
            await _log_step(state, "retrieve_chunks", "failed", error="No chunks available")
            return {**state, "error": "No content available for summary.", "status": "failed"}

        # Sort by score (descending) and take top chunks
        all_retrieved_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        top_chunks = all_retrieved_chunks[:8]  # Use top 8 chunks for better coverage

        await _log_step(
            state, "retrieve_chunks", "completed", details={"chunks_retrieved": len(top_chunks)}
        )

        return {
            **state,
            "document": document,
            "search_results": top_chunks,
            "status": "analyzing_quality",
        }
    except Exception as e:
        logger.error(f"Error retrieving chunks for summary: {str(e)}", exc_info=True)
        await _log_step(state, "retrieve_chunks", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


def _analyze_content_quality(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze content quality to detect repetitive/fluff content."""
    import re
    from collections import Counter

    if not chunks:
        return {
            "is_repetitive": False,
            "repetition_score": 0.0,
            "unique_content_ratio": 1.0,
            "has_substantive_content": False,
        }

    # Extract all text content
    all_text = " ".join(chunk.get("content", "") for chunk in chunks)
    words = re.findall(r"\b\w+\b", all_text.lower())

    if not words:
        return {
            "is_repetitive": False,
            "repetition_score": 0.0,
            "unique_content_ratio": 1.0,
            "has_substantive_content": False,
        }

    # Calculate word frequency
    word_freq = Counter(words)
    total_words = len(words)
    unique_words = len(word_freq)

    # Calculate repetition score (higher = more repetitive)
    top_words_count = sum(count for word, count in word_freq.most_common(10))
    repetition_score = top_words_count / total_words if total_words > 0 else 0.0

    # Calculate unique content ratio
    unique_content_ratio = unique_words / total_words if total_words > 0 else 1.0

    # Check for substantive content
    has_substantive_content = total_words > 50 and unique_content_ratio > 0.3

    # Consider repetitive if repetition_score > 0.5 or unique_content_ratio < 0.2
    is_repetitive = repetition_score > 0.5 or unique_content_ratio < 0.2

    return {
        "is_repetitive": is_repetitive,
        "repetition_score": repetition_score,
        "unique_content_ratio": unique_content_ratio,
        "has_substantive_content": has_substantive_content,
    }


async def _analyze_quality(state: SummaryState) -> SummaryState:
    """Analyze content quality and prepare combined text."""
    try:
        await _log_step(state, "analyze_quality", "started")

        top_chunks = state["search_results"]

        # Analyze content quality
        quality_metrics = _analyze_content_quality(top_chunks)

        # Combine chunk texts with diversity (ensure chunks are from different sections)
        chunk_texts = []
        chunk_indices_used = set()

        # First, add highest-scoring chunks
        for chunk in top_chunks[:5]:
            chunk_idx = chunk.get("chunk_index", 0)
            content = chunk.get("content", "")
            if content and chunk_idx not in chunk_indices_used:
                chunk_texts.append(content)
                chunk_indices_used.add(chunk_idx)

        # Then add chunks from different sections for diversity
        for chunk in top_chunks[5:]:
            chunk_idx = chunk.get("chunk_index", 0)
            content = chunk.get("content", "")
            # Only add if it's from a different section (not adjacent to existing chunks)
            if content and chunk_idx not in chunk_indices_used:
                # Check if chunk is too close to existing chunks
                is_diverse = True
                for existing_idx in chunk_indices_used:
                    if abs(chunk_idx - existing_idx) < 3:  # Within 3 chunks
                        is_diverse = False
                        break
                if is_diverse:
                    chunk_texts.append(content)
                    chunk_indices_used.add(chunk_idx)

        if not chunk_texts:
            # Fallback: use all chunks if diversity filtering removed everything
            chunk_texts = [chunk.get("content", "") for chunk in top_chunks[:5] if chunk.get("content")]

        combined_text = "\n\n".join(chunk_texts[:6])  # Use up to 6 diverse chunks

        await _log_step(
            state,
            "analyze_quality",
            "completed",
            details={
                "quality_metrics": quality_metrics,
                "combined_text_length": len(combined_text),
            },
        )

        return {
            **state,
            "quality_metrics": quality_metrics,
            "combined_text": combined_text,
            "status": "generating",
        }
    except Exception as e:
        logger.error(f"Error analyzing quality: {str(e)}", exc_info=True)
        await _log_step(state, "analyze_quality", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


async def _generate_summary(state: SummaryState) -> SummaryState:
    """Generate summary using LLM with structured output."""
    input_data = state["input_data"]
    llm = state["llm"]
    system_prompt = state["system_prompt"]
    document = state["document"]
    combined_text = state["combined_text"]
    quality_metrics = state["quality_metrics"]

    try:
        await _log_step(state, "generate_summary", "started")

        # Build enhanced prompt with conservatism instructions
        prompt_text = system_prompt.format(max_bullets=input_data.max_bullets)

        # Add quality-aware instructions
        if quality_metrics.get("is_repetitive"):
            prompt_text += "\n\nNOTE: The content appears to be repetitive. Focus on high-level themes and avoid repeating the same points multiple times."

        if not quality_metrics.get("has_substantive_content"):
            prompt_text += "\n\nNOTE: The content may lack substantive detail. Be conservative and focus on general themes rather than specific claims."

        user_prompt = f"Document title: {document.title or 'Untitled'}\n\nContent to summarize:\n{combined_text[:3000]}"

        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            ("user", user_prompt),
        ])

        # Use structured output
        structured_llm = llm.with_structured_output(SummaryResponse)
        chain = prompt | structured_llm
        response: SummaryResponse = await chain.ainvoke({})

        await _log_step(
            state,
            "generate_summary",
            "completed",
            details={"summary_length": len(response.summary) if response.summary else 0},
        )

        return {
            **state,
            "llm_response": response,
            "summary": response.summary,
            "status": "storing",
        }
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        await _log_step(state, "generate_summary", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


async def _store_summary(state: SummaryState) -> SummaryState:
    """Store summary in document."""
    input_data = state["input_data"]
    summary = state["summary"]
    db = state["db"]

    try:
        await _log_step(state, "store_summary", "started")

        if not summary:
            raise ValueError("No summary to store")

        from app.models.document import Document
        from sqlalchemy import select

        stmt = select(Document).where(Document.id == input_data.document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {input_data.document_id} not found")

        document.summary_text = summary
        await db.commit()
        await db.refresh(document)

        await _log_step(state, "store_summary", "completed")

        return {**state, "status": "completed"}
    except Exception as e:
        logger.error(f"Error storing summary: {str(e)}", exc_info=True)
        await db.rollback()
        await _log_step(state, "store_summary", "failed", error=str(e))
        return {**state, "error": str(e), "status": "failed"}


def _should_continue_after_retrieve(state: SummaryState) -> Literal["continue", "error"]:
    """Check if we should continue after retrieval."""
    if state.get("error") or state["status"] == "failed":
        return "error"
    return "continue"


def _should_continue_after_analyze(state: SummaryState) -> Literal["continue", "error"]:
    """Check if we should continue after quality analysis."""
    if state.get("error") or state["status"] == "failed":
        return "error"
    return "continue"


def _should_continue_after_generate(state: SummaryState) -> Literal["continue", "error"]:
    """Check if we should continue after generation."""
    if state.get("error") or state["status"] == "failed":
        return "error"
    return "continue"


async def _handle_error(state: SummaryState) -> SummaryState:
    """Handle errors in the workflow."""
    error_message = state.get("error", "Unknown summary generation error")
    await _log_step(state, "handle_error", "completed", error=error_message)
    return {**state, "status": "failed"}


def build_summary_graph(service_tools: Any, llm: Any, system_prompt: str, db: Any) -> StateGraph:
    """Build the summary generation graph.

    Args:
        service_tools: ServiceTools instance
        llm: LLM instance
        system_prompt: System prompt for summary generation
        db: Database session

    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(SummaryState)

    # Add nodes
    workflow.add_node("retrieve_chunks", _retrieve_chunks)
    workflow.add_node("analyze_quality", _analyze_quality)
    workflow.add_node("generate_summary", _generate_summary)
    workflow.add_node("store_summary", _store_summary)
    workflow.add_node("handle_error", _handle_error)

    # Define edges
    workflow.set_entry_point("retrieve_chunks")
    workflow.add_conditional_edges(
        "retrieve_chunks",
        _should_continue_after_retrieve,
        {
            "continue": "analyze_quality",
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "analyze_quality",
        _should_continue_after_analyze,
        {
            "continue": "generate_summary",
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "generate_summary",
        _should_continue_after_generate,
        {
            "continue": "store_summary",
            "error": "handle_error",
        },
    )
    workflow.add_edge("store_summary", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()

