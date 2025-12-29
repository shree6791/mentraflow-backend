"""Agent run service."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.services.base import BaseService


class AgentRunService(BaseService):
    """Service for agent run operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_run(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        agent_name: str,
        input_json: dict[str, Any],
        status: str = "queued",
    ) -> AgentRun:
        """Create a new agent run.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            agent_name: Name of the agent
            input_json: Input data as JSON
            status: Initial status (default: "queued")
        """
        agent_run = AgentRun(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=agent_name,
            status=status,
            input=input_json,
        )
        self.db.add(agent_run)
        await self._commit_and_refresh(agent_run)
        return agent_run

    async def update_status(
        self,
        run_id: uuid.UUID,
        status: str | None = None,
        output_json: dict[str, Any] | None = None,
        error: str | None = None,
        step: dict[str, Any] | None = None,
    ) -> AgentRun:
        """Update agent run status.
        
        Args:
            run_id: Agent run ID
            status: New status (e.g., "running", "succeeded", "failed") - None to keep current
            output_json: Optional output data
            error: Optional error message
            step: Optional step log entry to append
        """
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        result = await self.db.execute(stmt)
        agent_run = result.scalar_one_or_none()
        if not agent_run:
            raise ValueError(f"Agent run {run_id} not found")

        if status is not None:
            agent_run.status = status
        if output_json is not None:
            agent_run.output = output_json
        if error is not None:
            agent_run.error = error
        
        # Append step log if provided
        if step is not None:
            if agent_run.steps is None:
                agent_run.steps = []
            step["timestamp"] = datetime.now(timezone.utc).isoformat()
            agent_run.steps.append(step)

        if status and status in ("succeeded", "failed", "completed"):
            agent_run.finished_at = datetime.now(timezone.utc)

        await self._commit_and_refresh(agent_run)
        return agent_run

    async def complete_run(
        self,
        run_id: uuid.UUID,
        output_json: dict[str, Any] | None = None,
        status: str = "succeeded",
        error: str | None = None,
        step: dict[str, Any] | None = None,
    ) -> AgentRun:
        """Complete an agent run with output and status.
        
        This is a convenience method that calls update_status.
        """
        return await self.update_status(run_id, status, output_json, error, step)
    
    async def log_step(
        self,
        run_id: uuid.UUID,
        step_name: str,
        step_status: str,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AgentRun:
        """Log a step in the agent run.
        
        Args:
            run_id: Agent run ID
            step_name: Name of the step (e.g., "chunk", "embed", "upsert")
            step_status: Status of the step ("started", "completed", "failed")
            details: Optional details about the step (e.g., count, duration)
            error: Optional error message if step failed
        """
        step = {
            "name": step_name,
            "status": step_status,
        }
        if details:
            step["details"] = details
        if error:
            step["error"] = error
        
        return await self.update_status(run_id, None, step=step)

    async def get_active_runs(
        self,
        workspace_id: uuid.UUID | None = None,
        agent_name: str | None = None,
        document_id: uuid.UUID | None = None,
    ) -> list[AgentRun]:
        """Get active agent runs (queued or running).
        
        Args:
            workspace_id: Optional workspace ID filter
            agent_name: Optional agent name filter (e.g., "ingestion")
            document_id: Optional document ID filter (checks input_json for document_id)
            
        Returns:
            List of active agent runs
        """
        stmt = select(AgentRun).where(
            AgentRun.status.in_(["queued", "running"])
        )
        
        if workspace_id:
            stmt = stmt.where(AgentRun.workspace_id == workspace_id)
        if agent_name:
            stmt = stmt.where(AgentRun.agent_name == agent_name)
        
        result = await self.db.execute(stmt)
        runs = list(result.scalars().all())
        
        # Filter by document_id if provided (check input_json)
        if document_id:
            filtered_runs = []
            for run in runs:
                if run.input and isinstance(run.input, dict):
                    # Check if input contains document_id
                    if run.input.get("document_id") == str(document_id):
                        filtered_runs.append(run)
            return filtered_runs
        
        return runs

