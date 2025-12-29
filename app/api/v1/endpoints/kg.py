"""Knowledge Graph endpoints (v1.5)."""
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse

router = APIRouter()


class ConceptRead(BaseModel):
    """Schema for reading a concept."""
    id: uuid.UUID = Field(description="Concept ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    name: str = Field(description="Concept name")
    description: str | None = Field(default=None, description="Concept description")
    type: str | None = Field(default=None, description="Concept type")
    aliases: list[str] | None = Field(default=None, description="Concept aliases")
    tags: list[str] | None = Field(default=None, description="Concept tags")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata",
        alias="meta_data",  # Read from model's meta_data attribute
        serialization_alias="metadata",  # Serialize as metadata in API response
    )
    created_by: uuid.UUID | None = Field(default=None, description="Creator user ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EdgeRead(BaseModel):
    """Schema for reading a KG edge."""
    id: uuid.UUID = Field(description="Edge ID")
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    src_type: str = Field(description="Source type")
    src_id: uuid.UUID = Field(description="Source concept ID")
    rel_type: str = Field(description="Relation type")
    dst_type: str = Field(description="Destination type")
    dst_id: uuid.UUID = Field(description="Destination concept ID")
    weight: float | None = Field(default=None, description="Edge weight")
    evidence: dict[str, Any] | None = Field(default=None, description="Edge evidence")
    created_by: uuid.UUID | None = Field(default=None, description="Creator user ID")
    created_at: datetime = Field(description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/concepts",
    response_model=list[ConceptRead],
    responses={500: {"model": ErrorResponse}},
    summary="List concepts",
)
async def list_concepts(
    workspace_id: Annotated[uuid.UUID, Query(description="Workspace ID")],
    document_id: Annotated[uuid.UUID | None, Query(description="Filter by document ID")] = None,
    q: Annotated[str | None, Query(description="Search query (name/description)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[ConceptRead]:
    """List concepts, optionally filtered by document or search query."""
    try:
        from sqlalchemy import select, or_
        from app.models.concept import Concept
        
        stmt = select(Concept).where(Concept.workspace_id == workspace_id)
        
        # TODO: Add document_id filtering when concept-document relationship is added
        # if document_id:
        #     stmt = stmt.where(Concept.source_document_id == document_id)
        
        if q:
            # Simple text search on name and description
            stmt = stmt.where(
                or_(
                    Concept.name.ilike(f"%{q}%"),
                    Concept.description.ilike(f"%{q}%") if Concept.description else False,
                )
            )
        
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        concepts = list(result.scalars().all())
        return [ConceptRead.model_validate(c) for c in concepts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing concepts: {str(e)}")


@router.get(
    "/concepts/{concept_id}",
    response_model=ConceptRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get a concept",
)
async def get_concept(
    concept_id: Annotated[uuid.UUID, Path(description="Concept ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConceptRead:
    """Get a concept by ID."""
    try:
        from sqlalchemy import select
        from app.models.concept import Concept
        
        stmt = select(Concept).where(Concept.id == concept_id)
        result = await db.execute(stmt)
        concept = result.scalar_one_or_none()
        if not concept:
            raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")
        return ConceptRead.model_validate(concept)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting concept: {str(e)}")


@router.get(
    "/concepts/{concept_id}/neighbors",
    response_model=list[ConceptRead],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get concept neighbors",
)
async def get_concept_neighbors(
    concept_id: Annotated[uuid.UUID, Path(description="Concept ID")],
    depth: Annotated[int, Query(ge=1, le=3, description="Traversal depth (1-3)")] = 1,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[ConceptRead]:
    """Get neighboring concepts up to specified depth."""
    try:
        from sqlalchemy import select
        from app.models.concept import Concept
        from app.models.kg_edge import KGEdge
        
        # Get concept to verify it exists
        stmt = select(Concept).where(Concept.id == concept_id)
        result = await db.execute(stmt)
        concept = result.scalar_one_or_none()
        if not concept:
            raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")
        
        # Get neighbors via edges
        neighbor_ids = set()
        current_level = {concept_id}
        
        for _ in range(depth):
            next_level = set()
            # Find edges where src or dst is in current level
            stmt = select(KGEdge).where(
                (KGEdge.src_id.in_(current_level)) | (KGEdge.dst_id.in_(current_level))
            )
            result = await db.execute(stmt)
            edges = result.scalars().all()
            
            for edge in edges:
                if edge.src_id in current_level:
                    next_level.add(edge.dst_id)
                if edge.dst_id in current_level:
                    next_level.add(edge.src_id)
            
            neighbor_ids.update(next_level)
            current_level = next_level
        
        # Remove the original concept
        neighbor_ids.discard(concept_id)
        
        if not neighbor_ids:
            return []
        
        # Fetch neighbor concepts
        stmt = select(Concept).where(Concept.id.in_(neighbor_ids))
        result = await db.execute(stmt)
        neighbors = list(result.scalars().all())
        return [ConceptRead.model_validate(n) for n in neighbors]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting neighbors: {str(e)}")


@router.get(
    "/edges",
    response_model=list[EdgeRead],
    responses={500: {"model": ErrorResponse}},
    summary="List KG edges",
)
async def list_edges(
    workspace_id: Annotated[uuid.UUID, Query(description="Workspace ID")],
    concept_id: Annotated[uuid.UUID | None, Query(description="Filter by concept ID (src or dst)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[EdgeRead]:
    """List KG edges, optionally filtered by concept."""
    try:
        from sqlalchemy import select
        from app.models.kg_edge import KGEdge
        
        stmt = select(KGEdge).where(KGEdge.workspace_id == workspace_id)
        
        if concept_id:
            stmt = stmt.where(
                (KGEdge.src_id == concept_id) | (KGEdge.dst_id == concept_id)
            )
        
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        edges = list(result.scalars().all())
        return [EdgeRead.model_validate(e) for e in edges]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing edges: {str(e)}")

