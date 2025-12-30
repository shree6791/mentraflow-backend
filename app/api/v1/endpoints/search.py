"""Search endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.services.retrieval_service import RetrievalService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


class SearchRequest(BaseModel):
    """Request body for semantic search."""
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    query: str = Field(description="Search query")
    top_k: int = Field(default=8, ge=1, le=50, description="Number of results to return")
    document_id: uuid.UUID | None = Field(default=None, description="Optional document ID filter")


class SearchResult(BaseModel):
    """Search result item."""
    chunk_id: uuid.UUID = Field(description="Chunk ID")
    document_id: uuid.UUID = Field(description="Document ID")
    chunk_index: int = Field(description="Chunk index")
    score: float = Field(description="Similarity score")
    snippet: str | None = Field(default=None, description="Chunk text snippet")


class SearchResponse(BaseModel):
    """Search response."""
    results: list[SearchResult] = Field(description="Search results")
    query: str = Field(description="Original query")
    total: int = Field(description="Total number of results")


@router.post(
    "/search",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Semantic search",
)
async def search(
    request: SearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchResponse:
    """Perform semantic search across workspace documents. Only accessible by workspace members."""
    try:
        # Verify user has access to the workspace
        workspace_service = WorkspaceService(db)
        workspace = await workspace_service.get_workspace(request.workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {request.workspace_id} not found")
        
        # Check if user is owner or member
        is_owner = workspace.owner_id == current_user.id
        if not is_owner:
            from sqlalchemy import select
            from app.models.workspace_membership import WorkspaceMembership
            
            stmt = select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == request.workspace_id) &
                (WorkspaceMembership.user_id == current_user.id)
            )
            result = await db.execute(stmt)
            membership = result.scalar_one_or_none()
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to search in this workspace"
                )
        
        service = RetrievalService(db)
        results = await service.semantic_search(
            workspace_id=request.workspace_id,
            query=request.query,
            top_k=request.top_k,
            filters={"document_id": request.document_id} if request.document_id else None,
        )
        
        search_results = [
            SearchResult(
                chunk_id=uuid.UUID(r["chunk_id"]),
                document_id=uuid.UUID(r["document_id"]),
                chunk_index=r.get("chunk_index", 0),
                score=r.get("score", 0.0),
                snippet=r.get("text", "")[:200] if r.get("text") else None,  # First 200 chars
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")

