"""Insights and dashboard stats schemas."""

from pydantic import BaseModel, Field


class WorkspaceInsightsResponse(BaseModel):
    """Workspace-level insights for dashboard (SRS-based)."""

    average_mastery: float | None = Field(
        default=None,
        description="Average mastery 0-100 derived from ease_factor across user's cards with SRS state; null if no cards reviewed",
    )
    cards_due: int = Field(
        default=0,
        description="Number of flashcards due for review (due_at in past or null)",
    )
    total_cards_with_srs: int = Field(
        default=0,
        description="Number of flashcards that have at least one review (SRS state exists)",
    )
    total_flashcards: int = Field(
        default=0,
        description="Total number of user's flashcards in the workspace",
    )
    kg_concepts_count: int = Field(
        default=0,
        description="Number of knowledge graph concepts in the workspace",
    )
    documents_count: int = Field(
        default=0,
        description="Number of documents in the workspace",
    )
    recent_activity: int = Field(
        default=0,
        description="Number of documents uploaded in the current week (ISO week, Monday–Sunday)",
    )
