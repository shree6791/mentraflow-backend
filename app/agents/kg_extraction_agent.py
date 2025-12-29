"""Knowledge graph extraction agent using LangGraph."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.service_tools import ServiceTools
from app.agents.types import KGExtractionAgentInput, KGExtractionAgentOutput


class KGExtractionAgent(BaseAgent[KGExtractionAgentInput, KGExtractionAgentOutput]):
    """Agent for extracting knowledge graph from documents using LangGraph."""

    def __init__(
        self,
        db: AsyncSession,
        graph_registry: GraphRegistry | None = None,
        service_tools: ServiceTools | None = None,
    ):
        """Initialize KG extraction agent.
        
        Args:
            db: Database session
            graph_registry: Optional shared graph registry (uses singleton if not provided)
            service_tools: Optional ServiceTools instance (creates new one if not provided)
        """
        super().__init__(db, agent_name="kg_extraction")
        self.service_tools = service_tools or ServiceTools(db)
        # Use shared graph registry (singleton)
        self.graph_registry = graph_registry or GraphRegistry()
        # Get graph - graphs are stateless, service_tools/db passed in state
        self.graph = self.graph_registry.get_kg_extraction_graph(
            self.service_tools, db
        )
        # Get system prompt and llm from registry (shared across requests)
        self.system_prompt = self.graph_registry.kg_prompt
        self.llm = self.graph_registry.llm

    async def run(self, input_data: KGExtractionAgentInput) -> KGExtractionAgentOutput:
        """Run KG extraction agent."""
        return await self._execute_with_logging(
            input_data.workspace_id,
            input_data.user_id,
            input_data,
            self._run_internal,
        )

    async def _run_internal(self) -> KGExtractionAgentOutput:
        """Internal run method using LangGraph."""
        input_data = self._current_input

        # Initialize state (includes service_tools, llm, and system_prompt for graph nodes)
        from app.agents.graphs.kg_graph import KGExtractionState
        initial_state: KGExtractionState = {
            "input_data": input_data,
            "search_results": [],
            "context": "",
            "llm_response": None,
            "concepts_data": [],
            "created_concepts": [],
            "name_to_id": {},
            "edges_data": [],
            "created_edges": [],
            "extracted_concepts": [],
            "extracted_edges": [],
            "related_edges_created": [],
            "error": None,
            "status": "pending",
            "service_tools": self.service_tools,
            "llm": self.llm,
            "system_prompt": self.system_prompt,
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Handle early exit (no chunks)
        if not final_state.get("search_results"):
            return KGExtractionAgentOutput(
                concepts_written=0,
                edges_written=0,
                concepts=[],
                edges=[],
            )

        # Check for errors
        self._check_and_raise_error(final_state, "KG extraction failed")

        # Return output
        return KGExtractionAgentOutput(
            concepts_written=len(final_state["extracted_concepts"]),
            edges_written=len(final_state["extracted_edges"]),
            concepts=final_state["extracted_concepts"],
            edges=final_state["extracted_edges"],
        )
