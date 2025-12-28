"""Centralized LangGraph definitions."""
from app.agents.graphs.flashcard_graph import build_flashcard_graph
from app.agents.graphs.ingestion_graph import build_ingestion_graph
from app.agents.graphs.kg_graph import build_kg_extraction_graph
from app.agents.graphs.registry import GraphRegistry
from app.agents.graphs.study_chat_graph import build_study_chat_graph

__all__ = [
    "build_ingestion_graph",
    "build_flashcard_graph",
    "build_kg_extraction_graph",
    "build_study_chat_graph",
    "GraphRegistry",
]

