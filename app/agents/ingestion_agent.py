"""Ingestion agent for processing documents using LangGraph."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.service_tools import ServiceTools
from app.agents.types import IngestionAgentInput, IngestionAgentOutput


class IngestionAgent(BaseAgent[IngestionAgentInput, IngestionAgentOutput]):
    """Agent for ingesting and processing documents using LangGraph."""

    def __init__(
        self,
        db: AsyncSession,
        graph_registry: GraphRegistry | None = None,
        service_tools: ServiceTools | None = None,
    ):
        """Initialize ingestion agent.
        
        Args:
            db: Database session
            graph_registry: Optional shared graph registry (uses singleton if not provided)
            service_tools: Optional ServiceTools instance (creates new one if not provided)
        """
        super().__init__(db, agent_name="ingestion")
        self.service_tools = service_tools or ServiceTools(db)
        # Use shared graph registry (singleton)
        self.graph_registry = graph_registry or GraphRegistry()
        # Get graph - graphs are stateless, service_tools/db passed in state
        self.graph = self.graph_registry.get_ingestion_graph(self.service_tools, db)


    async def run(self, input_data: IngestionAgentInput) -> IngestionAgentOutput:
        """Run ingestion agent."""
        return await self._execute_with_logging(
            input_data.workspace_id,
            input_data.user_id,
            input_data,
            self._run_internal,
        )

    async def _run_internal(self) -> IngestionAgentOutput:
        """Internal run method using LangGraph."""
        input_data = self._current_input

        # Initialize state (includes service_tools and db for graph nodes)
        from app.agents.graphs.ingestion_graph import IngestionState
        initial_state: IngestionState = {
            "input_data": input_data,
            "document_id": input_data.document_id,
            "document": None,
            "chunks": [],
            "embeddings": [],
            "error": None,
            "status": "pending",
            "service_tools": self.service_tools,
            "db": self.db,
            "run_id": self._get_run_id(),  # Pass run_id for step logging
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Check for errors and update document status if needed
        if final_state.get("error") or final_state.get("status") == "failed":
            error_message = final_state.get("error", "Ingestion failed")
            # Update document status to failed (defense-in-depth)
            try:
                from app.services.document_service import DocumentService
                doc_service = DocumentService(self.db)
                await doc_service.update_document(
                    document_id=final_state["document_id"],
                    status="failed"
                )
            except Exception as e:
                # Log but don't fail - _handle_error should have updated status
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to update document status to failed: {str(e)}")
            
            raise ValueError(error_message)

        # Return output (run_id will be set by BaseAgent._execute_with_logging)
        return IngestionAgentOutput(
            document_id=final_state["document_id"],
            chunks_created=len(final_state["chunks"]),
            embeddings_created=len(final_state["embeddings"]),
            status="ready",  # Use "ready" to match document status after ingestion
            run_id=self._get_run_id(),
        )
