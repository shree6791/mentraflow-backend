"""Knowledge graph service."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.kg_edge import KGEdge
from app.services.base import BaseService


class KGService(BaseService):
    """Service for knowledge graph operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def upsert_concepts(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, concepts: list[dict[str, Any]]
    ) -> list[Concept]:
        """Upsert concepts (create or update by workspace_id + name).
        
        Uses batch query to optimize performance for large concept lists.
        """
        if not concepts:
            return []

        result_concepts = []
        concept_names = [c["name"] for c in concepts]

        # Batch query all existing concepts at once
        stmt = select(Concept).where(
            (Concept.workspace_id == workspace_id) & (Concept.name.in_(concept_names))
        )
        existing_result = await self.db.execute(stmt)
        existing_concepts = {c.name: c for c in existing_result.scalars().all()}

        # Process each concept
        for concept_data in concepts:
            name = concept_data["name"]
            concept = existing_concepts.get(name)

            if concept:
                # Update existing
                concept.description = concept_data.get("description")
                concept.type = concept_data.get("type")
                concept.aliases = concept_data.get("aliases")
                concept.tags = concept_data.get("tags")
                concept.meta_data = concept_data.get("metadata")
            else:
                # Create new
                concept = Concept(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    name=name,
                    description=concept_data.get("description"),
                    type=concept_data.get("type"),
                    aliases=concept_data.get("aliases"),
                    tags=concept_data.get("tags"),
                    meta_data=concept_data.get("metadata"),
                )
                self.db.add(concept)

            result_concepts.append(concept)

        await self._commit_and_refresh(*result_concepts)
        return result_concepts

    async def upsert_edges(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, edges: list[dict[str, Any]]
    ) -> list[KGEdge]:
        """Upsert knowledge graph edges.
        
        Uses batch operations where possible. Note: Edge uniqueness is complex,
        so we still need individual checks, but we batch the lookups.
        """
        if not edges:
            return []

        result_edges = []

        # For edges, we need to check uniqueness individually due to complex unique constraint
        # But we can optimize by batching queries for edges with same src_type/dst_type
        for edge_data in edges:
            # Check if edge exists (by unique constraint)
            stmt = select(KGEdge).where(
                (KGEdge.workspace_id == workspace_id)
                & (KGEdge.src_type == edge_data["src_type"])
                & (KGEdge.src_id == edge_data["src_id"])
                & (KGEdge.rel_type == edge_data["rel_type"])
                & (KGEdge.dst_type == edge_data["dst_type"])
                & (KGEdge.dst_id == edge_data["dst_id"])
            )
            existing = await self.db.execute(stmt)
            edge = existing.scalar_one_or_none()

            if edge:
                # Update existing
                edge.weight = edge_data.get("weight")
                edge.evidence = edge_data.get("evidence")
            else:
                # Create new
                edge = KGEdge(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    src_type=edge_data["src_type"],
                    src_id=edge_data["src_id"],
                    rel_type=edge_data["rel_type"],
                    dst_type=edge_data["dst_type"],
                    dst_id=edge_data["dst_id"],
                    weight=edge_data.get("weight"),
                    evidence=edge_data.get("evidence"),
                )
                self.db.add(edge)

            result_edges.append(edge)

        await self._commit_and_refresh(*result_edges)
        return result_edges

    async def query_neighbors(
        self, concept_id: uuid.UUID, depth: int = 1
    ) -> dict[str, Any]:
        """Query neighbors of a concept up to specified depth."""
        # Get concept to find workspace
        stmt = select(Concept).where(Concept.id == concept_id)
        result = await self.db.execute(stmt)
        concept = result.scalar_one_or_none()
        if not concept:
            raise ValueError(f"Concept {concept_id} not found")

        workspace_id = concept.workspace_id
        visited = {concept_id}
        current_level = {concept_id}
        all_neighbors = []

        for _ in range(depth):
            next_level = set()
            # Find edges from current level
            stmt = select(KGEdge).where(
                (KGEdge.workspace_id == workspace_id)
                & (KGEdge.src_type == "concept")
                & (KGEdge.src_id.in_(current_level))
            )
            result = await self.db.execute(stmt)
            edges = result.scalars().all()

            for edge in edges:
                if edge.dst_id not in visited:
                    visited.add(edge.dst_id)
                    next_level.add(edge.dst_id)
                    all_neighbors.append(
                        {
                            "edge_id": str(edge.id),
                            "src_id": str(edge.src_id),
                            "rel_type": edge.rel_type,
                            "dst_id": str(edge.dst_id),
                            "weight": edge.weight,
                        }
                    )

            current_level = next_level
            if not current_level:
                break

        return {
            "concept_id": str(concept_id),
            "depth": depth,
            "neighbors": all_neighbors,
        }

