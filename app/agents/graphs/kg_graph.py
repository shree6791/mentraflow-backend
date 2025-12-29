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
        "pending", "retrieving", "extracting", "upserting_concepts", "upserting_edges", "finding_relations", "completed", "failed"
    ]
    related_edges_created: list[Any]  # Edges created to existing concepts
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
    workflow.add_node("find_related_concepts", _find_related_concepts)  # Find relations to existing concepts
    workflow.add_node("build_output", _build_output)
    workflow.add_node("handle_error", _handle_error)

    # Define workflow edges (linear flow with error handling)
    workflow.set_entry_point("retrieve_chunks")
    
    # Retrieve chunks - can return early if empty, or continue/error
    workflow.add_conditional_edges(
        "retrieve_chunks",
        _should_continue_after_retrieve,
        {
            "continue": "extract_kg",
            "empty": END,  # Return early if no chunks
            "error": "handle_error",
        },
    )
    
    # Extract KG - continue or error
    workflow.add_conditional_edges(
        "extract_kg",
        _should_continue,
        {
            "continue": "prepare_concepts",
            "error": "handle_error",
        },
    )
    
    # Prepare and upsert concepts (sequential)
    workflow.add_edge("prepare_concepts", "upsert_concepts")
    workflow.add_conditional_edges(
        "upsert_concepts",
        _should_continue,
        {
            "continue": "build_name_mapping",
            "error": "handle_error",
        },
    )
    
    # Build name mapping, prepare edges, upsert edges (sequential)
    workflow.add_edge("build_name_mapping", "prepare_edges")
    workflow.add_edge("prepare_edges", "upsert_edges")
    workflow.add_conditional_edges(
        "upsert_edges",
        _should_continue,
        {
            "continue": "find_related_concepts",
            "error": "handle_error",
        },
    )
    
    # Find related concepts and create edges (optional - failures don't block)
    workflow.add_conditional_edges(
        "find_related_concepts",
        _should_continue,  # Always continue even on failure
        {
            "continue": "build_output",
            "error": "build_output",  # Continue to output even if relation finding fails
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
    """Prepare concepts data for upsert, filtering by quality and quantity limits."""
    from app.core.constants import MAX_CONCEPTS_PER_DOCUMENT, MIN_CONCEPT_CONFIDENCE
    
    response = state["llm_response"]
    concepts_data = []
    
    # Filter concepts by confidence threshold and sort by confidence (highest first)
    filtered_concepts = [
        concept for concept in response.concepts
        if concept.confidence >= MIN_CONCEPT_CONFIDENCE
    ]
    
    # Sort by confidence (descending) to prioritize highest quality
    filtered_concepts.sort(key=lambda c: c.confidence, reverse=True)
    
    # Apply quantity limit (keep top N concepts)
    limited_concepts = filtered_concepts[:MAX_CONCEPTS_PER_DOCUMENT]
    
    for concept in limited_concepts:
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
    """Prepare edges data for upsert, filtering by quality and quantity limits."""
    from app.core.constants import MAX_EDGES_PER_DOCUMENT, MIN_CONCEPT_CONFIDENCE
    
    response = state["llm_response"]
    name_to_id = state["name_to_id"]

    edges_data = []
    for edge in response.edges:
        src_id = name_to_id.get(edge.src_name)
        dst_id = name_to_id.get(edge.dst_name)

        # Only include edges where both concepts exist and confidence is high enough
        if src_id and dst_id and edge.confidence >= MIN_CONCEPT_CONFIDENCE:
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
    
    # Sort by confidence (descending) and limit quantity
    edges_data.sort(key=lambda e: e["evidence"]["confidence"], reverse=True)
    edges_data = edges_data[:MAX_EDGES_PER_DOCUMENT]

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


async def _find_related_concepts(state: KGExtractionState) -> KGExtractionState:
    """Find relations to existing concepts via semantic search in Qdrant.
    
    For each newly created concept:
    1. Generate embedding for the concept (name + description)
    2. Search Qdrant concepts collection for similar existing concepts
    3. Create edges between new concepts and similar existing concepts (similarity > 0.7)
    """
    import uuid
    import logging
    
    logger = logging.getLogger(__name__)
    input_data = state["input_data"]
    created_concepts = state.get("created_concepts", [])
    service_tools = state["service_tools"]
    
    # Similarity threshold for creating relations
    SIMILARITY_THRESHOLD = 0.7
    MAX_RELATIONS_PER_CONCEPT = 5  # Limit to top 5 similar concepts
    
    related_edges = []
    
    try:
        if not created_concepts:
            return {**state, "related_edges_created": [], "status": "finding_relations"}
        
        # Get embedding service
        from app.services.embedding_service import EmbeddingService
        from app.infrastructure.qdrant import QdrantClientWrapper
        
        embedding_service = EmbeddingService(service_tools.db)
        qdrant_client = QdrantClientWrapper()
        
        # Process each newly created concept
        for concept in created_concepts:
            try:
                # Generate embedding for concept (name + description)
                concept_text = concept.name
                if concept.description:
                    concept_text = f"{concept.name}: {concept.description}"
                
                # Generate embedding
                vector, _ = await embedding_service._generate_embedding(concept_text)
                
                # Search for similar existing concepts in Qdrant (same workspace, exclude current concept)
                # Note: We need to filter out the current concept and other newly created concepts
                new_concept_ids = {str(c.id) for c in created_concepts}
                
                search_results = await qdrant_client.search_concepts(
                    workspace_id=input_data.workspace_id,
                    query_vector=vector,
                    top_k=MAX_RELATIONS_PER_CONCEPT + len(created_concepts),  # Get extra to account for filtering
                    score_threshold=SIMILARITY_THRESHOLD,  # Filter at Qdrant level for efficiency
                )
                
                # Filter out newly created concepts (score threshold already applied by Qdrant)
                similar_concepts = [
                    r for r in search_results
                    if r.get("id") not in new_concept_ids
                ][:MAX_RELATIONS_PER_CONCEPT]
                
                # Create edges to similar existing concepts
                for similar in similar_concepts:
                    try:
                        existing_concept_id = uuid.UUID(similar["id"])
                        similarity_score = similar.get("score", 0.7)
                        
                        # Create bidirectional edge (related_to relationship)
                        edge_data = {
                            "src_type": "concept",
                            "src_id": concept.id,
                            "rel_type": "related_to",
                            "dst_type": "concept",
                            "dst_id": existing_concept_id,
                            "weight": float(similarity_score),
                            "evidence": {
                                "similarity_score": float(similarity_score),
                                "source": "semantic_search",
                                "method": "qdrant_vector_search",
                            },
                        }
                        
                        # Upsert edge (will skip if already exists due to unique constraint)
                        created_edge = await service_tools.kg_service.upsert_edges(
                            input_data.workspace_id,
                            input_data.user_id,
                            [edge_data],
                        )
                        
                        if created_edge:
                            related_edges.extend(created_edge)
                    except Exception as edge_error:
                        # Log but continue - don't fail entire operation
                        logger.warning(
                            f"Failed to create edge from {concept.id} to {similar.get('id')}: {str(edge_error)}"
                        )
                        continue
                
                # Store concept embedding in Qdrant for future searches
                # (This enables future concepts to find this one)
                try:
                    from datetime import datetime, timezone
                    points = [{
                        "id": str(concept.id),
                        "vector": vector,
                        "payload": {
                            "workspace_id": str(input_data.workspace_id),
                            "concept_id": str(concept.id),
                            "name": concept.name,
                            "concept_name": concept.name,  # For keyword indexing
                            "description": concept.description or "",
                            "created_at": int(datetime.now(timezone.utc).timestamp()),
                        },
                    }]
                    await qdrant_client.upsert_concept_vectors(
                        workspace_id=input_data.workspace_id,
                        points=points,
                    )
                except Exception as qdrant_error:
                    # Log but continue - embedding storage failure shouldn't block
                    logger.warning(
                        f"Failed to store concept embedding in Qdrant for {concept.id}: {str(qdrant_error)}"
                    )
                    
            except Exception as concept_error:
                # Log but continue processing other concepts
                logger.warning(
                    f"Failed to find relations for concept {concept.id}: {str(concept_error)}"
                )
                continue
        
        return {
            **state,
            "related_edges_created": related_edges,
            "status": "finding_relations",
        }
    except Exception as e:
        # Log but don't fail - relation finding is optional
        logger.warning(f"Error finding related concepts: {str(e)}", exc_info=True)
        return {
            **state,
            "related_edges_created": [],
            "status": "finding_relations",
        }


async def _build_output(state: KGExtractionState) -> KGExtractionState:
    """Build final output."""
    created_concepts = state["created_concepts"]
    created_edges = state["created_edges"]

    extracted_concepts = [
        ExtractedConcept(
            name=c.name,
            description=c.description,
            type=c.type,
            confidence=c.meta_data.get("confidence", 0.5) if c.meta_data else 0.5,
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


def _should_continue(state: KGExtractionState) -> Literal["continue", "error"]:
    """Check if we should continue to next step or handle error."""
    return "error" if state.get("error") else "continue"

