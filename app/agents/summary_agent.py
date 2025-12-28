"""Summary generation agent using LangGraph."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.service_tools import ServiceTools
from app.agents.types import SummaryAgentInput, SummaryAgentOutput


class SummaryAgent(BaseAgent[SummaryAgentInput, SummaryAgentOutput]):
    """Agent for generating document summaries using LangGraph."""

    def __init__(
        self,
        db: AsyncSession,
        graph_registry: GraphRegistry | None = None,
        service_tools: ServiceTools | None = None,
    ):
        """Initialize summary agent.

        Args:
            db: Database session
            graph_registry: Optional shared graph registry (uses singleton if not provided)
            service_tools: Optional ServiceTools instance (creates new one if not provided)
        """
        super().__init__(db, agent_name="summary")
        self.service_tools = service_tools or ServiceTools(db)
        # Use shared graph registry (singleton)
        self.graph_registry = graph_registry or GraphRegistry()
        # Get graph - graphs are stateless, service_tools/db passed in state
        self.graph = self.graph_registry.get_summary_graph(self.service_tools, self.graph_registry.llm, self.graph_registry.summary_prompt, db)
        # Get system prompt and llm from registry (shared across requests)
        self.system_prompt = self.graph_registry.summary_prompt
        self.llm = self.graph_registry.llm

    async def run(self, input_data: SummaryAgentInput) -> SummaryAgentOutput:
        """Run summary agent."""
        return await self._execute_with_logging(
            input_data.workspace_id,
            input_data.user_id,
            input_data,
            self._run_internal,
        )

    async def _run_internal(self) -> SummaryAgentOutput:
        """Internal run method using LangGraph."""
        input_data = self._current_input

        # Initialize state (includes service_tools, llm, system_prompt, and db for graph nodes)
        from app.agents.graphs.summary_graph import SummaryState
        initial_state: SummaryState = {
            "input_data": input_data,
            "document": None,
            "search_results": [],
            "quality_metrics": {},
            "combined_text": "",
            "llm_response": None,
            "summary": None,
            "error": None,
            "status": "pending",
            "service_tools": self.service_tools,
            "llm": self.llm,
            "system_prompt": self.system_prompt,
            "db": self.db,
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Handle errors from graph
        if final_state.get("error") or final_state["status"] == "failed":
            error_msg = final_state.get("error", "Summary generation failed")
            raise ValueError(error_msg)

        # Extract output from final state
        summary = final_state.get("summary", "")
        if not summary:
            raise ValueError("Summary generation completed but no summary was produced")

        return SummaryAgentOutput(
            document_id=input_data.document_id,
            summary=summary,
            summary_length=len(summary),
            run_id=getattr(self, "_current_run_id", None),
        )

