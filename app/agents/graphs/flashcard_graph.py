"""Centralized flashcard graph definition."""
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel
from langgraph.graph import END, StateGraph

from app.agents.types import FlashcardAgentInput, FlashcardPreview


class FlashcardCard(LangChainBaseModel):
    """Flashcard card structure for LLM."""

    front: str
    back: str
    card_type: str
    options: list[str] | None = None  # For MCQ: list of answer options (A, B, C, D)
    correct_answer: str | None = None  # For MCQ: the correct option (e.g., "A", "B", "C", "D")


class FlashcardList(LangChainBaseModel):
    """List of flashcards from LLM."""

    cards: list[FlashcardCard]


class FlashcardState(TypedDict):
    """State for flashcard agent graph."""

    input_data: FlashcardAgentInput
    search_results: list[dict]
    context: str
    llm_response: FlashcardList | None
    cards: list[dict]
    validated_cards: list[dict]  # Cards that passed validation
    dropped_cards: list[dict]  # Cards that were dropped with reasons
    flashcards: list[Any]
    preview: list[FlashcardPreview]
    error: str | None
    status: Literal["pending", "retrieving", "generating", "validating", "creating", "completed", "failed"]
    service_tools: Any
    llm: Any
    system_prompt: str
    batch_id: Any  # Batch/generation ID


def build_flashcard_graph(service_tools: Any, llm: Any, system_prompt: str) -> StateGraph:
    """Build the flashcard generation graph.
    
    Args:
        service_tools: ServiceTools instance
        llm: LLM instance
        system_prompt: System prompt for flashcard generation
        
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(FlashcardState)

    # Add nodes
    workflow.add_node("retrieve_chunks", _retrieve_chunks)
    workflow.add_node("generate_flashcards", _generate_flashcards)
    workflow.add_node("validate_cards", _validate_cards)  # New validation step
    workflow.add_node("create_flashcards", _create_flashcards)
    workflow.add_node("build_preview", _build_preview)
    workflow.add_node("handle_error", _handle_error)

    # Define workflow edges (linear flow with error handling)
    workflow.set_entry_point("retrieve_chunks")
    
    # Retrieve chunks - can return early if empty, or continue/error
    workflow.add_conditional_edges(
        "retrieve_chunks",
        _should_continue_after_retrieve,
        {
            "continue": "generate_flashcards",
            "empty": END,  # Return early if no chunks
            "error": "handle_error",
        },
    )
    
    # Generate flashcards - continue or error
    workflow.add_conditional_edges(
        "generate_flashcards",
        _should_continue,
        {
            "continue": "validate_cards",
            "error": "handle_error",
        },
    )
    
    # Validate cards - can return early if insufficient, or continue/error
    workflow.add_conditional_edges(
        "validate_cards",
        _should_continue_after_validate,
        {
            "continue": "create_flashcards",
            "insufficient": END,  # Not enough good cards
            "error": "handle_error",
        },
    )
    
    # Create flashcards and build preview (sequential)
    workflow.add_edge("create_flashcards", "build_preview")
    workflow.add_edge("build_preview", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


async def _retrieve_chunks(state: FlashcardState) -> FlashcardState:
    """Retrieve relevant chunks from document and check content quality."""
    input_data = state["input_data"]
    service_tools = state["service_tools"]
    
    try:
        # Use multiple semantic queries to get diverse chunks for flashcard generation
        # This is better than empty query which might not work well
        flashcard_queries = [
            "key terms definitions important concepts",
            "main ideas core principles",
            "examples explanations details",
        ]
        
        all_retrieved_chunks = []
        seen_chunk_ids = set()
        
        # Retrieve chunks using multiple semantic queries for diversity
        for query in flashcard_queries:
            search_results = await service_tools.retrieval_service.semantic_search(
                input_data.workspace_id,
                query=query,
                top_k=7,  # Get top 7 for each query (total ~20 chunks)
                filters={"document_id": str(input_data.source_document_id)},
            )
            
            # Add unique chunks (avoid duplicates)
            for result in search_results:
                chunk_id = result.get("chunk_id")
                if chunk_id and chunk_id not in seen_chunk_ids:
                    all_retrieved_chunks.append(result)
                    seen_chunk_ids.add(chunk_id)
        
        # If semantic retrieval didn't work (e.g., embeddings not ready), fallback to first chunks
        if not all_retrieved_chunks:
            from sqlalchemy import select
            from app.models.document_chunk import DocumentChunk
            stmt = select(DocumentChunk).where(
                DocumentChunk.document_id == input_data.source_document_id
            ).order_by(DocumentChunk.chunk_index).limit(20)
            db_result = await service_tools.db.execute(stmt)
            chunks = list(db_result.scalars().all())
            
            all_retrieved_chunks = [
                {
                    "chunk_id": str(chunk.id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "score": 1.0,  # Default score for fallback
                }
                for chunk in chunks if chunk.content
            ]
        
        return {
            **state,
            "search_results": all_retrieved_chunks,
            "status": "retrieving",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _generate_flashcards(state: FlashcardState) -> FlashcardState:
    """Generate flashcards using LLM."""
    import uuid as uuid_lib
    
    input_data = state["input_data"]
    search_results = state["search_results"]
    llm = state["llm"]
    system_prompt = state["system_prompt"]

    # Build context from chunks with chunk_id mapping
    context_parts = []
    for result in search_results:
        chunk_id = uuid_lib.UUID(result["chunk_id"])
        context_parts.append(
            f"[Chunk ID: {chunk_id}, Index: {result['chunk_index']}]:\n{result['content']}"
        )
    context = "\n\n".join(context_parts)

    try:
        # Generate flashcards using structured output
        structured_llm = llm.with_structured_output(FlashcardList)

        prompt = f"""{system_prompt}

Mode: {input_data.mode}

Document Content:
{context}

Generate flashcards based on the mode. Return a list of flashcards.
For each flashcard, you should reference which chunk IDs (from the Chunk ID markers above) were used to generate it."""

        response = await structured_llm.ainvoke(prompt)

        # Convert to service format with chunk_id tracking
        # Map card_type to match requested mode (validate in validation step)
        from app.core.constants import FLASHCARD_MODE_TO_CARD_TYPE
        expected_type = FLASHCARD_MODE_TO_CARD_TYPE.get(input_data.mode, "qa")
        
        # For now, we'll associate each card with all retrieved chunks
        # In a more sophisticated implementation, the LLM could specify which chunks
        # were used for each card, but for simplicity, we'll use all chunks
        all_chunk_ids = [uuid_lib.UUID(r["chunk_id"]) for r in search_results]
        
        cards = []
        for card in response.cards:
            # Ensure card_type matches mode (will be validated later)
            card_type = card.card_type
            if card_type != expected_type:
                # Try to map it
                if input_data.mode == "qa" and card_type == "qa":
                    card_type = "qa"  # OK
                elif input_data.mode == "mcq" and card_type == "mcq":
                    card_type = "mcq"  # OK
                # Otherwise, use expected type
                else:
                    card_type = expected_type
            
            card_data = {
                "front": card.front,
                "back": card.back,
                "card_type": card_type,
                "source_chunk_ids": all_chunk_ids,  # Associate with all retrieved chunks
            }
            
            # For MCQ cards, store options and correct answer in metadata
            if card_type == "mcq" and card.options and card.correct_answer:
                # Normalize back field to be just the letter (A, B, C, or D)
                # LLM might return full answer text, but we need just the letter
                back_normalized = card.back.strip().upper()
                # Extract letter if it's in the back text, otherwise use correct_answer
                if back_normalized in ["A", "B", "C", "D"]:
                    card_data["back"] = back_normalized
                else:
                    # Use the correct_answer from metadata as the back
                    card_data["back"] = card.correct_answer.upper()
                
                card_data["metadata"] = {
                    "options": card.options,
                    "correct_answer": card.correct_answer,
                }
            
            cards.append(card_data)

        return {
            **state,
            "context": context,
            "llm_response": response,
            "cards": cards,
            "status": "generating",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "generating"}


def _validate_card(card: dict, requested_mode: str) -> tuple[bool, str | None]:
    """Validate a single flashcard card.
    
    Args:
        card: Card dictionary with front, back, card_type, and optionally options/correct_answer for MCQ
        requested_mode: Requested mode (qa or mcq)
        
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    front = card.get("front", "")
    back = card.get("back", "")
    card_type = card.get("card_type", "")
    metadata = card.get("metadata", {})
    
    # Check for empty fields
    if not front or not back:
        return False, "empty_field"
    
    # Check card_type matches requested mode
    from app.core.constants import FLASHCARD_MODE_TO_CARD_TYPE
    expected_type = FLASHCARD_MODE_TO_CARD_TYPE.get(requested_mode, "qa")
    if card_type != expected_type:
        return False, "card_type_mismatch"
    
    # MCQ-specific validation
    # NOTE: Document-specificity is enforced by the strict prompt instructions.
    # The LLM is instructed to ONLY use information from provided chunks and never use outside knowledge.
    if card_type == "mcq":
        options = metadata.get("options", [])
        correct_answer = metadata.get("correct_answer", "")
        
        # Check options exist and have exactly 4
        if not options or len(options) != 4:
            return False, "mcq_invalid_options"
        
        # Check correct_answer is valid (A, B, C, or D)
        if correct_answer not in ["A", "B", "C", "D"]:
            return False, "mcq_invalid_answer"
        
        # Check back matches correct_answer letter
        # Back should be normalized to just the letter by this point (done in card processing)
        back_normalized = back.strip().upper()
        if back_normalized != correct_answer:
            return False, "mcq_answer_mismatch"
        
        # Check each option is not empty and reasonable length
        for option in options:
            if not option or len(option.strip()) < 3:
                return False, "mcq_option_too_short"
            if len(option) > 200:  # Reasonable limit for MCQ options
                return False, "mcq_option_too_long"
        
        # Check front (question) length
        MAX_FRONT_LENGTH = 300  # MCQ questions can be longer
        MIN_FRONT_LENGTH = 10
        if len(front) > MAX_FRONT_LENGTH:
            return False, "front_too_long"
        if len(front) < MIN_FRONT_LENGTH:
            return False, "front_too_short"
        
        return True, None
    
    # Non-MCQ validation (existing logic)
    # Check length limits
    MAX_FRONT_LENGTH = 200
    MAX_BACK_LENGTH = 300
    
    if len(front) > MAX_FRONT_LENGTH:
        return False, "front_too_long"
    
    if len(back) > MAX_BACK_LENGTH:
        return False, "back_too_long"
    
    # Check minimum length (too short might be trivial)
    MIN_FRONT_LENGTH = 5
    MIN_BACK_LENGTH = 5
    
    if len(front) < MIN_FRONT_LENGTH:
        return False, "front_too_short"
    
    if len(back) < MIN_BACK_LENGTH:
        return False, "back_too_short"
    
    # Check for trivial content (same front and back, or very similar)
    if front.strip().lower() == back.strip().lower():
        return False, "trivial_content"
    
    # Check for repetitive content (back is just a repeat of front)
    if back.strip().lower().startswith(front.strip().lower()):
        return False, "repetitive_content"
    
    return True, None


async def _validate_cards(state: FlashcardState) -> FlashcardState:
    """Validate and prune flashcards."""
    input_data = state["input_data"]
    cards = state.get("cards", [])
    
    validated_cards = []
    dropped_cards = []
    
    for card in cards:
        is_valid, reason = _validate_card(card, input_data.mode)
        if is_valid:
            validated_cards.append(card)
        else:
            dropped_cards.append({
                "card": card,
                "reason": reason or "unknown",
            })
    
    return {
        **state,
        "validated_cards": validated_cards,
        "dropped_cards": dropped_cards,
        "cards": validated_cards,  # Update cards to only include validated ones
        "status": "validating",
    }


def _should_continue_after_validate(
    state: FlashcardState
) -> Literal["continue", "insufficient", "error"]:
    """Check if we should continue after validation."""
    if state.get("error"):
        return "error"
    
    validated_cards = state.get("validated_cards", [])
    
    # If no valid cards, return insufficient
    if not validated_cards:
        return "insufficient"
    
    # If less than 3 good cards, might want to return insufficient
    # But let's allow it and let the user decide
    # Minimum threshold: at least 1 valid card
    if len(validated_cards) < 1:
        return "insufficient"
    
    return "continue"


async def _create_flashcards(state: FlashcardState) -> FlashcardState:
    """Create flashcards in database."""
    input_data = state["input_data"]
    validated_cards = state.get("validated_cards", [])  # Use validated cards
    service_tools = state["service_tools"]
    batch_id = state.get("batch_id")

    try:
        flashcards = await service_tools.flashcard_service.create_flashcards_from_text(
            input_data.workspace_id,
            input_data.user_id,
            input_data.source_document_id,
            validated_cards,
            batch_id=batch_id,
        )
        return {
            **state,
            "flashcards": flashcards,
            "status": "creating",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _build_preview(state: FlashcardState) -> FlashcardState:
    """Build preview of flashcards."""
    from app.agents.types import FlashcardPreview
    
    validated_cards = state.get("validated_cards", [])
    preview = [
        FlashcardPreview(
            front=card["front"],
            back=card["back"],
            card_type=card["card_type"],
            source_chunk_ids=card.get("source_chunk_ids", []),
        )
        for card in validated_cards[:5]  # Show first 5 validated cards as preview
    ]
    return {**state, "preview": preview, "status": "completed"}


async def _handle_error(state: FlashcardState) -> FlashcardState:
    """Handle errors in the workflow."""
    return state


def _should_continue(state: FlashcardState) -> Literal["continue", "error"]:
    """Check if we should continue to next step or handle error."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_retrieve(
    state: FlashcardState
) -> Literal["continue", "empty", "error"]:
    """Check if we should continue after retrieving chunks."""
    if state.get("error"):
        return "error"
    if not state.get("search_results"):
        return "empty"
    return "continue"

