"""Agent router for selecting and running agents."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.flashcard_agent import FlashcardAgent
from app.agents.graphs.registry import GraphRegistry
from app.agents.ingestion_agent import IngestionAgent
from app.agents.kg_extraction_agent import KGExtractionAgent
from app.agents.study_chat_agent import StudyChatAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.service_tools import ServiceTools
from app.agents.types import (
    FlashcardAgentInput,
    FlashcardAgentOutput,
    IngestionAgentInput,
    IngestionAgentOutput,
    KGExtractionAgentInput,
    KGExtractionAgentOutput,
    StudyChatAgentInput,
    StudyChatAgentOutput,
    SummaryAgentInput,
    SummaryAgentOutput,
)


class AgentRouter:
    """Router for selecting and executing agents.
    
    Uses a shared GraphRegistry (singleton) to reuse compiled graphs
    across all requests, improving performance.
    """

    def __init__(self, db: AsyncSession):
        """Initialize agent router.
        
        Args:
            db: Database session for this request
        """
        self.db = db
        self.service_tools = ServiceTools(db)
        
        # Get shared graph registry (singleton - same instance across all requests)
        self.graph_registry = GraphRegistry()
        
        # Initialize agents with shared graph registry and LLM
        # Each agent gets the registry and will pass service_tools/db when accessing graphs
        self._agents = {
            "ingestion": IngestionAgent(
                db, graph_registry=self.graph_registry, service_tools=self.service_tools
            ),
            "study_chat": StudyChatAgent(
                db, graph_registry=self.graph_registry
            ),
            "flashcard": FlashcardAgent(
                db, graph_registry=self.graph_registry, service_tools=self.service_tools
            ),
            "kg_extraction": KGExtractionAgent(
                db, graph_registry=self.graph_registry, service_tools=self.service_tools
            ),
            "summary": SummaryAgent(
                db, graph_registry=self.graph_registry, service_tools=self.service_tools
            ),
        }

    async def run_ingestion(
        self, input_data: IngestionAgentInput, skip_logging: bool = False
    ) -> IngestionAgentOutput:
        """Run ingestion agent."""
        agent = self._agents["ingestion"]
        if skip_logging:
            return await agent.run_without_logging(input_data)
        return await agent.run(input_data)

    async def run_study_chat(
        self, input_data: StudyChatAgentInput, skip_logging: bool = False
    ) -> StudyChatAgentOutput:
        """Run study chat agent."""
        agent = self._agents["study_chat"]
        if skip_logging:
            return await agent.run_without_logging(input_data)
        return await agent.run(input_data)

    async def run_flashcard(
        self, input_data: FlashcardAgentInput, skip_logging: bool = False
    ) -> FlashcardAgentOutput:
        """Run flashcard agent."""
        agent = self._agents["flashcard"]
        if skip_logging:
            return await agent.run_without_logging(input_data)
        return await agent.run(input_data)

    async def run_kg_extraction(
        self, input_data: KGExtractionAgentInput, skip_logging: bool = False
    ) -> KGExtractionAgentOutput:
        """Run KG extraction agent."""
        agent = self._agents["kg_extraction"]
        if skip_logging:
            return await agent.run_without_logging(input_data)
        return await agent.run(input_data)

    async def run_summary(
        self, input_data: SummaryAgentInput, skip_logging: bool = False
    ) -> SummaryAgentOutput:
        """Run summary agent."""
        agent = self._agents["summary"]
        if skip_logging:
            return await agent.run_without_logging(input_data)
        return await agent.run(input_data)

