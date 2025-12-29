"""Pydantic IO models for agents."""
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import (
    DEFAULT_FLASHCARD_MODE,
    DEFAULT_SUMMARY_MAX_BULLETS,
    SUMMARY_MAX_BULLETS_MAX,
    SUMMARY_MAX_BULLETS_MIN,
)


# IngestionAgent
class IngestionAgentInput(BaseModel):
    """Input for IngestionAgent."""

    document_id: uuid.UUID = Field(description="Document ID to process")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    raw_text: str | None = Field(default=None, description="Optional raw text to store")


class IngestionAgentOutput(BaseModel):
    """Output from IngestionAgent."""

    document_id: uuid.UUID = Field(description="Processed document ID")
    chunks_created: int = Field(description="Number of chunks created")
    embeddings_created: int = Field(description="Number of embeddings created")
    status: str = Field(description="Final document status")
    run_id: uuid.UUID | None = Field(default=None, description="Agent run ID for tracking")


# StudyChatAgent
class StudyChatAgentInput(BaseModel):
    """Input for StudyChatAgent."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    message: str = Field(description="User's question or message")
    document_id: uuid.UUID | None = Field(default=None, description="Optional document ID to focus on")
    conversation_id: uuid.UUID | None = Field(default=None, description="Optional conversation ID for follow-up questions")
    previous_messages: list[dict] | None = Field(default=None, description="Previous messages in conversation (for context)")
    top_k: int = Field(default=8, ge=1, le=50, description="Number of chunks to retrieve (default: 8)")


class Citation(BaseModel):
    """Citation reference."""

    chunk_id: uuid.UUID = Field(description="Chunk ID")
    document_id: uuid.UUID = Field(description="Document ID")
    chunk_index: int = Field(description="Chunk index in document")
    score: float = Field(description="Relevance score")


class SuggestedNote(BaseModel):
    """Suggested note from chat."""

    title: str = Field(description="Note title")
    body: str = Field(description="Note content")
    document_id: uuid.UUID | None = Field(default=None, description="Related document ID")


class StudyChatAgentOutput(BaseModel):
    """Output from StudyChatAgent."""

    answer: str = Field(description="Answer to user's question")
    citations: list[Citation] = Field(description="Citations from retrieved chunks")
    suggested_note: SuggestedNote | None = Field(default=None, description="Optional suggested note")
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Confidence score for the answer (0.0-1.0)")
    insufficient_info: bool = Field(default=False, description="Whether the retrieved chunks contain insufficient information to answer")


# FlashcardAgent
class FlashcardAgentInput(BaseModel):
    """Input for FlashcardAgent."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    source_document_id: uuid.UUID = Field(description="Source document ID")
    mode: str = Field(
        default="mcq",
        description="Generation mode: qa or mcq (default: mcq)"
    )


class FlashcardPreview(BaseModel):
    """Preview of a flashcard."""

    front: str = Field(description="Front side")
    back: str = Field(description="Back side")
    card_type: str = Field(description="Card type")
    source_chunk_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Chunk IDs used to generate this flashcard"
    )


class FlashcardAgentOutput(BaseModel):
    """Output from FlashcardAgent."""

    flashcards_created: int = Field(description="Number of flashcards created")
    preview: list[FlashcardPreview] = Field(description="Preview of created flashcards")
    reason: str | None = Field(
        default=None,
        description="Reason for empty result (e.g., 'no_content', 'insufficient_chunks')",
    )
    dropped_count: int = Field(
        default=0, description="Number of cards dropped due to validation failures"
    )
    dropped_reasons: list[dict] = Field(
        default_factory=list,
        description="List of dropped cards with reasons (e.g., [{'card': {...}, 'reason': 'back_too_long'}])",
    )
    batch_id: uuid.UUID | None = Field(
        default=None, description="Batch/generation ID for this flashcard generation run"
    )


# KGExtractionAgent
class KGExtractionAgentInput(BaseModel):
    """Input for KGExtractionAgent."""

    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    source_document_id: uuid.UUID = Field(description="Source document ID")


class ExtractedConcept(BaseModel):
    """Extracted concept."""

    name: str = Field(description="Concept name")
    description: str | None = Field(default=None, description="Concept description")
    type: str | None = Field(default=None, description="Concept type")
    confidence: float = Field(description="Confidence score")


class ExtractedEdge(BaseModel):
    """Extracted knowledge graph edge."""

    src_type: str = Field(description="Source entity type")
    src_id: uuid.UUID = Field(description="Source entity ID")
    rel_type: str = Field(description="Relationship type")
    dst_type: str = Field(description="Destination entity type")
    dst_id: uuid.UUID = Field(description="Destination entity ID")
    weight: float | None = Field(default=None, description="Edge weight")
    confidence: float = Field(description="Confidence score")


class KGExtractionAgentOutput(BaseModel):
    """Output from KGExtractionAgent."""

    concepts_written: int = Field(description="Number of concepts written")
    edges_written: int = Field(description="Number of edges written")
    concepts: list[ExtractedConcept] = Field(description="Extracted concepts")
    edges: list[ExtractedEdge] = Field(description="Extracted edges")


# SummaryAgent
class SummaryAgentInput(BaseModel):
    """Input for SummaryAgent."""

    document_id: uuid.UUID = Field(description="Document ID to summarize")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    max_bullets: int = Field(
        default=DEFAULT_SUMMARY_MAX_BULLETS,
        ge=SUMMARY_MAX_BULLETS_MIN,
        le=SUMMARY_MAX_BULLETS_MAX,
        description=f"Maximum number of bullet points in summary (default: {DEFAULT_SUMMARY_MAX_BULLETS})"
    )


class SummaryAgentOutput(BaseModel):
    """Output from SummaryAgent."""

    document_id: uuid.UUID = Field(description="Document ID that was summarized")
    summary: str = Field(description="Generated summary text")
    summary_length: int = Field(description="Length of summary in characters")
    run_id: uuid.UUID | None = Field(default=None, description="Agent run ID for tracking")

