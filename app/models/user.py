"""User model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.user_preference import UserPreference
    from app.models.workspace import Workspace
    from app.models.workspace_membership import WorkspaceMembership
    from app.models.agent_run import AgentRun
    from app.models.concept import Concept
    from app.models.kg_edge import KGEdge
    from app.models.document import Document
    from app.models.flashcard import Flashcard
    from app.models.note import Note
    from app.models.flashcard_review import FlashcardReview
    from app.models.flashcard_srs_state import FlashcardSRSState
    from app.models.conversation import Conversation


class User(Base):
    """User model."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    preference: Mapped["UserPreference | None"] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    owned_workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="owner", foreign_keys="Workspace.owner_user_id"
    )
    workspace_memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="user", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="user", cascade="all, delete-orphan"
    )
    created_concepts: Mapped[list["Concept"]] = relationship(
        "Concept", back_populates="creator", foreign_keys="Concept.created_by"
    )
    created_kg_edges: Mapped[list["KGEdge"]] = relationship(
        "KGEdge", back_populates="creator", foreign_keys="KGEdge.created_by"
    )
    created_documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="creator", foreign_keys="Document.created_by"
    )
    flashcards: Mapped[list["Flashcard"]] = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )
    flashcard_reviews: Mapped[list["FlashcardReview"]] = relationship(
        "FlashcardReview", back_populates="user", cascade="all, delete-orphan"
    )
    flashcard_srs_states: Mapped[list["FlashcardSRSState"]] = relationship(
        "FlashcardSRSState", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

