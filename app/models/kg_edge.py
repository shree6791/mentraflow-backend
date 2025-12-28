"""Knowledge graph edge model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Float, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User


class KGEdge(Base):
    """Knowledge graph edge model."""

    __tablename__ = "kg_edges"
    __table_args__ = (
        Index("ix_kg_edges_workspace_id", "workspace_id"),
        Index("ix_kg_edges_created_by", "created_by"),
        Index("ix_kg_edges_src_id", "src_id"),  # For graph traversal queries
        Index("ix_kg_edges_dst_id", "dst_id"),  # For graph traversal queries
        UniqueConstraint(
            "src_type",
            "src_id",
            "rel_type",
            "dst_type",
            "dst_id",
            name="uq_kg_edges_src_rel_dst",
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
    src_type: Mapped[str] = mapped_column(Text, nullable=False)
    src_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rel_type: Mapped[str] = mapped_column(Text, nullable=False)
    dst_type: Mapped[str] = mapped_column(Text, nullable=False)
    dst_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="kg_edges"
    )
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_kg_edges", foreign_keys=[created_by]
    )

