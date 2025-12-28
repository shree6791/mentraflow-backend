"""Concept model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User


class Concept(Base):
    """Concept model."""

    __tablename__ = "concepts"
    __table_args__ = (
        Index("ix_concepts_workspace_id", "workspace_id"),
        Index("ix_concepts_created_by", "created_by"),
        UniqueConstraint("workspace_id", "name", name="uq_concepts_workspace_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, name="metadata")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
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
        "Workspace", back_populates="concepts"
    )
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_concepts", foreign_keys=[created_by]
    )

