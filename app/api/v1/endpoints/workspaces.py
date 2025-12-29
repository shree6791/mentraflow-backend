"""Workspace endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.post(
    "/workspaces",
    response_model=WorkspaceRead,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create a new workspace",
)
async def create_workspace(
    request: WorkspaceCreate,
    owner_username: Annotated[str, Query(description="Owner username")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Create a new workspace.
    
    The owner is identified by username (e.g., "shree6791").
    """
    try:
        # Look up user by username
        from app.services.user_service import UserService
        user_service = UserService(db)
        user = await user_service.get_user_by_username(owner_username)
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with username '{owner_username}' not found. Please sign up first.",
            )
        
        service = WorkspaceService(db)
        workspace = await service.create_workspace(
            owner_id=user.id,
            name=request.name,
            plan_tier=request.plan_tier,
        )
        return WorkspaceRead.model_validate(workspace)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating workspace: {str(e)}")


@router.get(
    "/workspaces",
    response_model=list[WorkspaceRead],
    responses={500: {"model": ErrorResponse}},
    summary="List workspaces",
)
async def list_workspaces(
    owner_id: Annotated[uuid.UUID | None, Query(description="Filter by owner user ID")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[WorkspaceRead]:
    """List workspaces, optionally filtered by owner."""
    try:
        service = WorkspaceService(db)
        workspaces = await service.list_workspaces(owner_id=owner_id)
        return [WorkspaceRead.model_validate(w) for w in workspaces]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing workspaces: {str(e)}")


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get a workspace",
)
async def get_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Get a workspace by ID."""
    try:
        service = WorkspaceService(db)
        workspace = await service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        return WorkspaceRead.model_validate(workspace)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workspace: {str(e)}")


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRead,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update a workspace",
)
async def update_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    request: WorkspaceCreate,  # Reuse for partial update
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Update a workspace."""
    try:
        service = WorkspaceService(db)
        workspace = await service.update_workspace(
            workspace_id=workspace_id,
            name=request.name,
            plan_tier=request.plan_tier,
        )
        return WorkspaceRead.model_validate(workspace)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating workspace: {str(e)}")


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete a workspace",
)
async def delete_workspace(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a workspace (cascade deletes all related data)."""
    try:
        service = WorkspaceService(db)
        await service.delete_workspace(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting workspace: {str(e)}")

