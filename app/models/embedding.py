"""Embedding model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class Embedding(Base):
    """Embedding model."""

    __tablename__ = "embeddings"
    __table_args__ = (
        Index("ix_embeddings_workspace_id", "workspace_id"),
        Index("ix_embeddings_entity_id", "entity_id"),  # For lookups by entity
        Index("ix_embeddings_entity_type", "entity_type"),  # For filtering by entity type
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "model",
            name="uq_embeddings_entity_type_entity_id_model",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    dims: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_store: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="embeddings"
    )

