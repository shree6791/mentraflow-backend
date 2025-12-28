"""Workspace model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace_membership import WorkspaceMembership
    from app.models.agent_run import AgentRun
    from app.models.concept import Concept
    from app.models.embedding import Embedding
    from app.models.kg_edge import KGEdge
    from app.models.document import Document
    from app.models.flashcard import Flashcard
    from app.models.note import Note
    from app.models.conversation import Conversation


class Workspace(Base):
    """Workspace model."""

    __tablename__ = "workspaces"
    __table_args__ = (Index("ix_workspaces_owner_user_id", "owner_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Note: CASCADE means deleting the owner user will delete the entire workspace
    # and all its data. Consider implementing ownership transfer before user deletion.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_tier: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_workspaces", foreign_keys=[owner_user_id]
    )
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="workspace", cascade="all, delete-orphan"
    )
    concepts: Mapped[list["Concept"]] = relationship(
        "Concept", back_populates="workspace", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="workspace", cascade="all, delete-orphan"
    )
    kg_edges: Mapped[list["KGEdge"]] = relationship(
        "KGEdge", back_populates="workspace", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="workspace", cascade="all, delete-orphan"
    )
    flashcards: Mapped[list["Flashcard"]] = relationship(
        "Flashcard", back_populates="workspace", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="workspace", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="workspace", cascade="all, delete-orphan"
    )

