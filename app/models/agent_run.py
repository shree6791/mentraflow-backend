"""Agent run model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User


class AgentRun(Base):
    """Agent run model."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_workspace_id", "workspace_id"),
        Index("ix_agent_runs_user_id", "user_id"),
        Index("ix_agent_runs_agent_name", "agent_name"),  # For filtering by agent type
        Index("ix_agent_runs_status", "status"),  # For filtering by status (queued, running, completed, failed)
        Index("ix_agent_runs_started_at", "started_at"),  # For time-based queries (recent runs, cleanup)
        Index("ix_agent_runs_workspace_status", "workspace_id", "status"),  # Composite index for common query pattern
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    input: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)  # Step-by-step progress logs
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="agent_runs"
    )
    user: Mapped["User"] = relationship("User", back_populates="agent_runs")

