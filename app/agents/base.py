"""Base agent class with logging and tracing."""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.registry import GraphRegistry
from app.services.agent_run_service import AgentRunService

InputModel = TypeVar("InputModel")
OutputModel = TypeVar("OutputModel")


class BaseAgent(ABC, Generic[InputModel, OutputModel]):
    """Base agent class with logging and tracing.
    
    Uses centralized LLM client from GraphRegistry for better performance,
    reliability, and scalability.
    """

    def __init__(
        self,
        db: AsyncSession,
        agent_name: str,
        model_name: str | None = None,
        graph_registry: GraphRegistry | None = None,
    ):
        """Initialize base agent.

        Args:
            db: Database session
            agent_name: Name of the agent for logging
            model_name: Optional model name override (not used if graph_registry provided)
            graph_registry: Optional shared GraphRegistry (uses singleton if not provided)
        """
        self.db = db
        self.agent_name = agent_name
        self.agent_run_service = AgentRunService(db)
        
        # Use centralized LLM from GraphRegistry (singleton)
        # This ensures single connection pool and better performance
        self.graph_registry = graph_registry or GraphRegistry()
        self.llm = self.graph_registry.llm

    @abstractmethod
    async def run(self, input_data: InputModel) -> OutputModel:
        """Run the agent with input and return output.

        Args:
            input_data: Input model instance

        Returns:
            Output model instance
        """
        pass

    @abstractmethod
    async def _run_internal(self) -> OutputModel:
        """Internal run method (called by run_without_logging).
        
        This method should be implemented by subclasses to perform
        the actual agent logic without logging.
        
        Returns:
            Output model instance
        """
        pass

    async def run_without_logging(self, input_data: InputModel) -> OutputModel:
        """Run agent without logging (for async execution).
        
        This method bypasses the normal logging and directly executes the agent.
        Status transitions should be handled externally.
        
        Args:
            input_data: Input model instance
            
        Returns:
            Output model instance
        """
        # Store input for access in _run_internal
        self._current_input = input_data
        try:
            # Call the internal run method
            return await self._run_internal()
        finally:
            # Clean up
            if hasattr(self, "_current_input"):
                delattr(self, "_current_input")

    async def _log_run_start(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        input_json: dict[str, Any],
        initial_status: str = "running",
    ) -> uuid.UUID:
        """Log agent run start and return run ID.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            input_json: Input data as JSON
            initial_status: Initial status (default: "running", use "queued" for async)
        """
        agent_run = await self.agent_run_service.create_run(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=self.agent_name,
            input_json=input_json,
            status=initial_status,
        )
        return agent_run.id

    async def _log_run_start_execution(self, run_id: uuid.UUID):
        """Update status to running when execution actually starts."""
        await self.agent_run_service.update_status(run_id, "running")

    async def _log_run_complete(
        self,
        run_id: uuid.UUID,
        output_json: dict[str, Any] | None = None,
        status: str = "succeeded",
        error: str | None = None,
    ):
        """Log agent run completion."""
        await self.agent_run_service.complete_run(
            run_id=run_id,
            output_json=output_json,
            status=status,
            error=error,
        )

    def _get_run_id(self) -> uuid.UUID | None:
        """Get current run ID if available."""
        return getattr(self, "_current_run_id", None)

    def _check_and_raise_error(
        self, final_state: dict[str, Any], default_error: str = "Agent execution failed"
    ) -> None:
        """Check final state for errors and raise if found.
        
        Args:
            final_state: Final state dictionary from graph execution
            default_error: Default error message if error not found in state
            
        Raises:
            ValueError: If error is found in final state
        """
        if final_state.get("error") or final_state.get("status") == "failed":
            error_message = final_state.get("error", default_error)
            raise ValueError(error_message)

    async def _execute_with_logging(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        input_data: InputModel,
        execute_fn: callable,
    ) -> OutputModel:
        """Execute agent with logging wrapper."""
        run_id = None
        try:
            # Store input for access in execute_fn
            self._current_input = input_data

            # Log start
            input_json = input_data.model_dump() if hasattr(input_data, "model_dump") else {}
            run_id = await self._log_run_start(workspace_id, user_id, input_json)
            
            # Store run_id for access in execute_fn
            self._current_run_id = run_id

            # Execute
            output = await execute_fn()
            
            # Add run_id to output if it has a run_id field
            if hasattr(output, "run_id"):
                output.run_id = run_id

            # Log success
            output_json = output.model_dump() if hasattr(output, "model_dump") else {}
            await self._log_run_complete(run_id, output_json=output_json, status="succeeded")

            return output
        except Exception as e:
            # Log error
            if run_id:
                await self._log_run_complete(
                    run_id, status="failed", error=str(e)
                )
            raise
        finally:
            # Clean up
            if hasattr(self, "_current_input"):
                delattr(self, "_current_input")
            if hasattr(self, "_current_run_id"):
                delattr(self, "_current_run_id")

