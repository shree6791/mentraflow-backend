"""Centralized KG extraction graph definition."""
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel
from langgraph.graph import END, StateGraph

from app.agents.types import (
    ExtractedConcept,
    ExtractedEdge,
    KGExtractionAgentInput,
)


class KGConcept(LangChainBaseModel):
    """Concept structure for LLM."""

    name: str
    description: str | None = None
    type: str | None = None
    confidence: float


class KGEdgeData(LangChainBaseModel):
    """Edge structure for LLM."""

    src_name: str
    rel_type: str
    dst_name: str
    weight: float | None = None
    confidence: float


class KGExtraction(LangChainBaseModel):
    """Knowledge graph extraction from LLM."""

    concepts: list[KGConcept]
    edges: list[KGEdgeData]


class KGExtractionState(TypedDict):
    """State for KG extraction agent graph."""

    input_data: KGExtractionAgentInput
    search_results: list[dict]
    context: str
    llm_response: KGExtraction | None
    concepts_data: list[dict]
    created_concepts: list[Any]
    name_to_id: dict[str, Any]
    edges_data: list[dict]
    created_edges: list[Any]
    extracted_concepts: list[ExtractedConcept]
    extracted_edges: list[ExtractedEdge]
    error: str | None
    status: Literal[
        "pending", "retrieving", "extracting", "upserting_concepts", "upserting_edges", "completed", "failed"
    ]
    service_tools: Any
    llm: Any
    system_prompt: str


def build_kg_extraction_graph(service_tools: Any, llm: Any, system_prompt: str) -> StateGraph:
    """Build the KG extraction graph.
    
    Args:
        service_tools: ServiceTools instance
        llm: LLM instance
        system_prompt: System prompt for KG extraction
        
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(KGExtractionState)

    # Add nodes
    workflow.add_node("retrieve_chunks", _retrieve_chunks)
    workflow.add_node("extract_kg", _extract_kg)
    workflow.add_node("prepare_concepts", _prepare_concepts)
    workflow.add_node("upsert_concepts", _upsert_concepts)
    workflow.add_node("build_name_mapping", _build_name_mapping)
    workflow.add_node("prepare_edges", _prepare_edges)
    workflow.add_node("upsert_edges", _upsert_edges)
    workflow.add_node("build_output", _build_output)
    workflow.add_node("handle_error", _handle_error)

    # Define edges
    workflow.set_entry_point("retrieve_chunks")
    workflow.add_conditional_edges(
        "retrieve_chunks",
        _should_continue_after_retrieve,
        {
            "continue": "extract_kg",
            "empty": END,  # Return early if no chunks
            "error": "handle_error",
        },
    )
    workflow.add_conditional_edges(
        "extract_kg",
        _should_continue_after_extract,
        {
            "continue": "prepare_concepts",
            "error": "handle_error",
        },
    )
    workflow.add_edge("prepare_concepts", "upsert_concepts")
    workflow.add_conditional_edges(
        "upsert_concepts",
        _should_continue_after_upsert_concepts,
        {
            "continue": "build_name_mapping",
            "error": "handle_error",
        },
    )
    workflow.add_edge("build_name_mapping", "prepare_edges")
    workflow.add_edge("prepare_edges", "upsert_edges")
    workflow.add_conditional_edges(
        "upsert_edges",
        _should_continue_after_upsert_edges,
        {
            "continue": "build_output",
            "error": "handle_error",
        },
    )
    workflow.add_edge("build_output", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


async def _retrieve_chunks(state: KGExtractionState) -> KGExtractionState:
    """Retrieve relevant chunks."""
    input_data = state["input_data"]
    service_tools = state["service_tools"]
    try:
        search_results = await service_tools.retrieval_service.semantic_search(
            input_data.workspace_id,
            query="",  # Empty query to get all chunks
            top_k=20,
            filters={"document_id": str(input_data.source_document_id)},
        )
        return {
            **state,
            "search_results": search_results,
            "status": "retrieving",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _extract_kg(state: KGExtractionState) -> KGExtractionState:
    """Extract KG using LLM."""
    input_data = state["input_data"]
    search_results = state["search_results"]
    llm = state["llm"]
    system_prompt = state["system_prompt"]

    # Build context
    context = "\n\n".join([r["content"] for r in search_results])

    try:
        # Extract using structured output
        structured_llm = llm.with_structured_output(KGExtraction)

        prompt = f"""{system_prompt}

Document Content:
{context}

Extract concepts and relationships. Be conservative with confidence scores."""

        response = await structured_llm.ainvoke(prompt)

        return {
            **state,
            "context": context,
            "llm_response": response,
            "status": "extracting",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _prepare_concepts(state: KGExtractionState) -> KGExtractionState:
    """Prepare concepts data for upsert."""
    response = state["llm_response"]
    concepts_data = []
    for concept in response.concepts:
        concepts_data.append(
            {
                "name": concept.name,
                "description": concept.description,
                "type": concept.type,
                "aliases": None,
                "tags": None,
                "metadata": {"confidence": concept.confidence},
            }
        )
    return {**state, "concepts_data": concepts_data}


async def _upsert_concepts(state: KGExtractionState) -> KGExtractionState:
    """Upsert concepts to database."""
    input_data = state["input_data"]
    concepts_data = state["concepts_data"]
    service_tools = state["service_tools"]

    try:
        created_concepts = await service_tools.kg_service.upsert_concepts(
            input_data.workspace_id,
            input_data.user_id,
            concepts_data,
        )
        return {
            **state,
            "created_concepts": created_concepts,
            "status": "upserting_concepts",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _build_name_mapping(state: KGExtractionState) -> KGExtractionState:
    """Build name to ID mapping for edges."""
    created_concepts = state["created_concepts"]
    name_to_id = {c.name: c.id for c in created_concepts}
    return {**state, "name_to_id": name_to_id}


async def _prepare_edges(state: KGExtractionState) -> KGExtractionState:
    """Prepare edges data for upsert."""
    response = state["llm_response"]
    name_to_id = state["name_to_id"]

    edges_data = []
    for edge in response.edges:
        src_id = name_to_id.get(edge.src_name)
        dst_id = name_to_id.get(edge.dst_name)

        if src_id and dst_id:
            edges_data.append(
                {
                    "src_type": "concept",
                    "src_id": src_id,
                    "rel_type": edge.rel_type,
                    "dst_type": "concept",
                    "dst_id": dst_id,
                    "weight": edge.weight,
                    "evidence": {"confidence": edge.confidence},
                }
            )

    return {**state, "edges_data": edges_data}


async def _upsert_edges(state: KGExtractionState) -> KGExtractionState:
    """Upsert edges to database."""
    input_data = state["input_data"]
    edges_data = state["edges_data"]
    service_tools = state["service_tools"]

    try:
        created_edges = await service_tools.kg_service.upsert_edges(
            input_data.workspace_id,
            input_data.user_id,
            edges_data,
        )
        return {
            **state,
            "created_edges": created_edges,
            "status": "upserting_edges",
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


async def _build_output(state: KGExtractionState) -> KGExtractionState:
    """Build final output."""
    created_concepts = state["created_concepts"]
    created_edges = state["created_edges"]

    extracted_concepts = [
        ExtractedConcept(
            name=c.name,
            description=c.description,
            type=c.type,
            confidence=c.metadata.get("confidence", 0.5) if c.metadata else 0.5,
        )
        for c in created_concepts
    ]

    extracted_edges = [
        ExtractedEdge(
            src_type="concept",
            src_id=e.src_id,
            rel_type=e.rel_type,
            dst_type="concept",
            dst_id=e.dst_id,
            weight=e.weight,
            confidence=e.evidence.get("confidence", 0.5) if e.evidence else 0.5,
        )
        for e in created_edges
    ]

    return {
        **state,
        "extracted_concepts": extracted_concepts,
        "extracted_edges": extracted_edges,
        "status": "completed",
    }


async def _handle_error(state: KGExtractionState) -> KGExtractionState:
    """Handle errors in the workflow."""
    return state


def _should_continue_after_retrieve(
    state: KGExtractionState
) -> Literal["continue", "empty", "error"]:
    """Check if we should continue after retrieving chunks."""
    if state.get("error"):
        return "error"
    if not state.get("search_results"):
        return "empty"
    return "continue"


def _should_continue_after_extract(
    state: KGExtractionState
) -> Literal["continue", "error"]:
    """Check if we should continue after extraction."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_upsert_concepts(
    state: KGExtractionState
) -> Literal["continue", "error"]:
    """Check if we should continue after upserting concepts."""
    return "error" if state.get("error") else "continue"


def _should_continue_after_upsert_edges(
    state: KGExtractionState
) -> Literal["continue", "error"]:
    """Check if we should continue after upserting edges."""
    return "error" if state.get("error") else "continue"

