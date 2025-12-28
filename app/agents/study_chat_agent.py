"""Study chat agent using LangGraph."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.service_tools import ServiceTools
from app.agents.types import StudyChatAgentInput, StudyChatAgentOutput


class StudyChatAgent(BaseAgent[StudyChatAgentInput, StudyChatAgentOutput]):
    """Agent for answering study questions with citations using LangGraph."""

    def __init__(
        self, db: AsyncSession, graph_registry: GraphRegistry | None = None
    ):
        """Initialize study chat agent.
        
        Args:
            db: Database session
            graph_registry: Optional shared GraphRegistry (uses singleton if not provided)
        """
        super().__init__(db, agent_name="study_chat", graph_registry=graph_registry)
        self.service_tools = ServiceTools(db)
        # Use shared graph registry (singleton)
        self.graph_registry = graph_registry or GraphRegistry()
        # Get graph - graphs are stateless, service_tools/db passed in state
        self.graph = self.graph_registry.get_study_chat_graph(
            self.service_tools, db
        )
        # Get system prompt and llm from registry (shared across requests)
        self.system_prompt = self.graph_registry.study_chat_prompt
        self.llm = self.graph_registry.llm

    async def run(self, input_data: StudyChatAgentInput) -> StudyChatAgentOutput:
        """Run study chat agent."""
        return await self._execute_with_logging(
            input_data.workspace_id,
            input_data.user_id,
            input_data,
            self._run_internal,
        )

    async def _run_internal(self) -> StudyChatAgentOutput:
        """Internal run method using LangGraph."""
        input_data = self._current_input

        # Initialize state (includes service_tools, llm, and system_prompt for graph nodes)
        from app.agents.graphs.study_chat_graph import StudyChatState
        initial_state: StudyChatState = {
            "input_data": input_data,
            "reformulated_query": "",
            "search_results": [],
            "context": "",
            "retrieved_chunk_ids": [],  # List of chunk_id strings
            "chunk_id_to_citation": {},
            "llm_response": None,
            "valid_citations": [],
            "suggested_note": None,
            "confidence_score": 0.0,
            "insufficient_info": False,
            "answer": "",
            "error": None,
            "status": "pending",
            "service_tools": self.service_tools,
            "llm": self.llm,
            "system_prompt": self.system_prompt,
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Check for errors
        if final_state.get("error") or final_state["status"] == "failed":
            # Error handling is done in the graph, but we can add additional logging here
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Study chat failed: {final_state.get('error', 'Unknown error')}")

        # Return output from final state
        return StudyChatAgentOutput(
            answer=final_state["answer"],
            citations=final_state["valid_citations"],
            suggested_note=final_state["suggested_note"],
            confidence_score=final_state["confidence_score"],
            insufficient_info=final_state["insufficient_info"],
        )

