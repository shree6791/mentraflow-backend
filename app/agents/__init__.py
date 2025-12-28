"""Agents module."""
from app.agents.base import BaseAgent
from app.agents.flashcard_agent import FlashcardAgent
from app.agents.ingestion_agent import IngestionAgent
from app.agents.kg_extraction_agent import KGExtractionAgent
from app.agents.router import AgentRouter
from app.agents.study_chat_agent import StudyChatAgent
from app.agents.types import (
    FlashcardAgentInput,
    FlashcardAgentOutput,
    IngestionAgentInput,
    IngestionAgentOutput,
    KGExtractionAgentInput,
    KGExtractionAgentOutput,
    StudyChatAgentInput,
    StudyChatAgentOutput,
)

__all__ = [
    "BaseAgent",
    "IngestionAgent",
    "StudyChatAgent",
    "FlashcardAgent",
    "KGExtractionAgent",
    "AgentRouter",
    "IngestionAgentInput",
    "IngestionAgentOutput",
    "StudyChatAgentInput",
    "StudyChatAgentOutput",
    "FlashcardAgentInput",
    "FlashcardAgentOutput",
    "KGExtractionAgentInput",
    "KGExtractionAgentOutput",
]
