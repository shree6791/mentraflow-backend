"""Flashcard generation agent using LangGraph."""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.service_tools import ServiceTools
from app.agents.types import FlashcardAgentInput, FlashcardAgentOutput


class FlashcardAgent(BaseAgent[FlashcardAgentInput, FlashcardAgentOutput]):
    """Agent for generating flashcards from documents using LangGraph."""

    def __init__(
        self,
        db: AsyncSession,
        graph_registry: GraphRegistry | None = None,
        service_tools: ServiceTools | None = None,
    ):
        """Initialize flashcard agent.
        
        Args:
            db: Database session
            graph_registry: Optional shared graph registry (uses singleton if not provided)
            service_tools: Optional ServiceTools instance (creates new one if not provided)
        """
        super().__init__(db, agent_name="flashcard")
        self.service_tools = service_tools or ServiceTools(db)
        # Use shared graph registry (singleton)
        self.graph_registry = graph_registry or GraphRegistry()
        # Get graph - graphs are stateless, service_tools/db passed in state
        self.graph = self.graph_registry.get_flashcard_graph(self.service_tools, db)
        # Get system prompt and llm from registry (shared across requests)
        self.system_prompt = self.graph_registry.flashcard_prompt
        self.llm = self.graph_registry.llm

    async def run(self, input_data: FlashcardAgentInput) -> FlashcardAgentOutput:
        """Run flashcard agent."""
        return await self._execute_with_logging(
            input_data.workspace_id,
            input_data.user_id,
            input_data,
            self._run_internal,
        )

    async def _run_internal(self) -> FlashcardAgentOutput:
        """Internal run method using LangGraph."""
        input_data = self._current_input

        # Generate batch_id for this generation run
        batch_id = uuid.uuid4()

        # Initialize state (includes service_tools, llm, and system_prompt for graph nodes)
        from app.agents.graphs.flashcard_graph import FlashcardState
        initial_state: FlashcardState = {
            "input_data": input_data,
            "search_results": [],
            "context": "",
            "llm_response": None,
            "cards": [],
            "validated_cards": [],
            "dropped_cards": [],
            "flashcards": [],
            "preview": [],
            "error": None,
            "status": "pending",
            "service_tools": self.service_tools,
            "llm": self.llm,
            "system_prompt": self.system_prompt,
            "batch_id": batch_id,
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Handle early exit (no chunks)
        if not final_state.get("search_results"):
            return FlashcardAgentOutput(
                flashcards_created=0,
                preview=[],
                reason="no_content",  # Explicit reason for empty result
                dropped_count=0,
                dropped_reasons=[],
                batch_id=batch_id,
            )

        # Check for insufficient content (validation filtered everything out)
        validated_cards = final_state.get("validated_cards", [])
        if not validated_cards:
            dropped_cards = final_state.get("dropped_cards", [])
            return FlashcardAgentOutput(
                flashcards_created=0,
                preview=[],
                reason="insufficient_content",  # All cards were dropped
                dropped_count=len(dropped_cards),
                dropped_reasons=dropped_cards,
                batch_id=batch_id,
            )

        # Check for errors
        if final_state.get("error") or final_state.get("status") == "failed":
            raise ValueError(final_state.get("error", "Flashcard generation failed"))

        # Get dropped cards info
        dropped_cards = final_state.get("dropped_cards", [])

        # Return output
        return FlashcardAgentOutput(
            flashcards_created=len(final_state["flashcards"]),
            preview=final_state["preview"],
            dropped_count=len(dropped_cards),
            dropped_reasons=dropped_cards,
            batch_id=batch_id,
        )
