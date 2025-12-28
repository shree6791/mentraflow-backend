"""Centralized graph registry for managing LangGraph instances."""
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs import (
    build_flashcard_graph,
    build_ingestion_graph,
    build_kg_extraction_graph,
    build_study_chat_graph,
    build_summary_graph,
)
from app.agents.service_tools import ServiceTools
from app.core.config import settings


class GraphRegistry:
    """Centralized registry for LangGraph instances.
    
    This registry creates graphs once and reuses them across requests.
    Graphs are stateless - service_tools and db are passed in state at runtime.
    
    This is a singleton pattern - graphs are created once on first access
    and reused for all subsequent requests.
    """

    _instance: "GraphRegistry | None" = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize graph registry (only once due to singleton pattern)."""
        if self._initialized:
            return

        # Initialize LLM (shared across all requests)
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Load prompts once
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.flashcard_prompt = (prompts_dir / "flashcard.txt").read_text()
        self.kg_prompt = (prompts_dir / "kg_extraction.txt").read_text()
        self.study_chat_prompt = (prompts_dir / "study_chat.txt").read_text()
        self.summary_prompt = (prompts_dir / "summary.txt").read_text()

        # Initialize graphs (lazy loading - graphs created on first access)
        # Note: Graphs are stateless - service_tools and db are passed in state
        self._ingestion_graph: Any | None = None
        self._flashcard_graph: Any | None = None
        self._kg_extraction_graph: Any | None = None
        self._study_chat_graph: Any | None = None
        self._summary_graph: Any | None = None

        self._initialized = True

    def get_ingestion_graph(self, service_tools: ServiceTools, db: AsyncSession) -> Any:
        """Get or create ingestion graph.
        
        Args:
            service_tools: ServiceTools instance for this request
            db: Database session for this request
            
        Returns:
            Compiled LangGraph instance
        """
        if self._ingestion_graph is None:
            self._ingestion_graph = build_ingestion_graph(service_tools, db)
        return self._ingestion_graph

    def get_flashcard_graph(self, service_tools: ServiceTools, db: AsyncSession) -> Any:
        """Get or create flashcard graph.
        
        Args:
            service_tools: ServiceTools instance for this request
            db: Database session for this request
            
        Returns:
            Compiled LangGraph instance
        """
        if self._flashcard_graph is None:
            self._flashcard_graph = build_flashcard_graph(
                service_tools, self.llm, self.flashcard_prompt
            )
        return self._flashcard_graph

    def get_kg_extraction_graph(
        self, service_tools: ServiceTools, db: AsyncSession
    ) -> Any:
        """Get or create KG extraction graph.
        
        Args:
            service_tools: ServiceTools instance for this request
            db: Database session for this request
            
        Returns:
            Compiled LangGraph instance
        """
        if self._kg_extraction_graph is None:
            self._kg_extraction_graph = build_kg_extraction_graph(
                service_tools, self.llm, self.kg_prompt
            )
        return self._kg_extraction_graph

    def get_study_chat_graph(
        self, service_tools: ServiceTools, db: AsyncSession
    ) -> Any:
        """Get or create study chat graph.
        
        Args:
            service_tools: ServiceTools instance for this request
            db: Database session for this request
            
        Returns:
            Compiled LangGraph instance
        """
        if self._study_chat_graph is None:
            self._study_chat_graph = build_study_chat_graph(
                service_tools, self.llm, self.study_chat_prompt
            )
        return self._study_chat_graph

    def get_summary_graph(
        self, service_tools: ServiceTools, llm: Any, system_prompt: str, db: AsyncSession
    ) -> Any:
        """Get or create summary graph.
        
        Args:
            service_tools: ServiceTools instance for this request
            llm: LLM instance
            system_prompt: System prompt for summary generation
            db: Database session for this request
            
        Returns:
            Compiled LangGraph instance
        """
        if self._summary_graph is None:
            self._summary_graph = build_summary_graph(
                service_tools, llm, system_prompt, db
            )
        return self._summary_graph

    def get_all_graphs(
        self, service_tools: ServiceTools, db: AsyncSession
    ) -> dict[str, Any]:
        """Get all graphs as a dictionary.
        
        Args:
            service_tools: ServiceTools instance for this request
            db: Database session for this request
            
        Returns:
            Dictionary mapping graph names to graph instances
        """
        return {
            "ingestion": self.get_ingestion_graph(service_tools, db),
            "flashcard": self.get_flashcard_graph(service_tools, db),
            "kg_extraction": self.get_kg_extraction_graph(service_tools, db),
            "study_chat": self.get_study_chat_graph(service_tools, db),
            "summary": self.get_summary_graph(service_tools, self.llm, self.summary_prompt, db),
        }

