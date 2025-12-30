"""Agent runs endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.services.agent_run_service import AgentRunService

router = APIRouter()


class AgentRunRead(BaseModel):
    """Schema for reading an agent run."""
    id: uuid.UUID = Field(description="Agent run ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    agent_name: str = Field(description="Agent name")
    status: str = Field(description="Run status")
    input: dict = Field(description="Input data")
    output: dict | None = Field(default=None, description="Output data")
    error: str | None = Field(default=None, description="Error message")
    steps: list[dict] | None = Field(default=None, description="Step-by-step progress logs")
    started_at: str | None = Field(default=None, description="Start timestamp")
    finished_at: str | None = Field(default=None, description="Finish timestamp")
    created_at: str = Field(description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/agent-runs/{run_id}",
    response_model=AgentRunRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get an agent run",
)
async def get_agent_run(
    run_id: Annotated[uuid.UUID, Path(description="Agent run ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRunRead:
    """Get an agent run by ID. Only accessible by the run owner."""
    try:
        from sqlalchemy import select
        from app.models.agent_run import AgentRun
        
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        result = await db.execute(stmt)
        agent_run = result.scalar_one_or_none()
        if not agent_run:
            raise HTTPException(status_code=404, detail=f"Agent run {run_id} not found")
        
        # Authorization check: ensure user owns the agent run
        if agent_run.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this agent run"
            )
        
        return AgentRunRead.model_validate(agent_run)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting agent run: {str(e)}")


@router.get(
    "/agent-runs",
    response_model=list[AgentRunRead],
    responses={500: {"model": ErrorResponse}},
    summary="List agent runs",
)
async def list_agent_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_id: Annotated[uuid.UUID | None, Query(description="Filter by workspace ID")] = None,
    agent_name: Annotated[str | None, Query(description="Filter by agent name")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[AgentRunRead]:
    """List agent runs for the authenticated user, optionally filtered by workspace, agent, or status."""
    try:
        from sqlalchemy import select
        from app.models.agent_run import AgentRun
        
        # Only show agent runs for the authenticated user
        stmt = select(AgentRun).where(AgentRun.user_id == current_user.id)
        if workspace_id:
            stmt = stmt.where(AgentRun.workspace_id == workspace_id)
        if agent_name:
            stmt = stmt.where(AgentRun.agent_name == agent_name)
        if status:
            stmt = stmt.where(AgentRun.status == status)
        stmt = stmt.order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        agent_runs = list(result.scalars().all())
        return [AgentRunRead.model_validate(r) for r in agent_runs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing agent runs: {str(e)}")

