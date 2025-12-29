"""Background task functions for agent execution."""
import uuid
from typing import Any, Callable

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.router import AgentRouter
from app.services.agent_run_service import AgentRunService
from app.tasks.runner import run_background_task


async def execute_agent_async(
    agent_name: str,
    agent_method: Callable,
    input_data: Any,
    run_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Execute an agent asynchronously with proper status transitions.
    
    Status flow: queued -> running -> succeeded/failed
    
    Args:
        agent_name: Name of the agent
        agent_method: Method to call on AgentRouter (should accept skip_logging parameter)
        input_data: Input data for the agent
        run_id: Pre-created run ID
        db: Database session
    """
    agent_run_service = AgentRunService(db)

    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Update status to running
        await agent_run_service.update_status(run_id, "running")

        # Execute agent with skip_logging=True to avoid duplicate run creation
        result = await agent_method(input_data, skip_logging=True)

        # Update status to succeeded
        # Use mode='json' to convert UUIDs and other non-JSON types to strings
        if hasattr(result, "model_dump"):
            output_json = result.model_dump(mode='json')
        else:
            output_json = {}
        await agent_run_service.update_status(
            run_id, "succeeded", output_json=output_json
        )
    except Exception as e:
        # Update status to failed
        logger.error(f"{agent_name} agent failed for run {run_id}: {str(e)}", exc_info=True)
        await agent_run_service.update_status(
            run_id, "failed", error=str(e)
        )
        # Re-raise to ensure it's logged by the task runner
        raise


def add_agent_task(
    background_tasks: BackgroundTasks,
    agent_name: str,
    agent_method: Callable,
    input_data: Any,
    run_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Add an agent execution task to background tasks.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        agent_name: Name of the agent
        agent_method: Method to call on AgentRouter
        input_data: Input data for the agent
        run_id: Pre-created run ID
        db: Database session
    """
    task_coro = execute_agent_async(agent_name, agent_method, input_data, run_id, db)
    context = {
        "agent_name": agent_name,
        "run_id": str(run_id),
    }
    background_tasks.add_task(
        run_background_task,
        task_coro,
        db,
        context,
    )

