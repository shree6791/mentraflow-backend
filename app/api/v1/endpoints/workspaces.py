"""Workspace endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.infrastructure.database import get_db
from app.models.user import User
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Create a new workspace for the authenticated user."""
    try:
        service = WorkspaceService(db)
        workspace = await service.create_workspace(
            owner_id=current_user.id,
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[WorkspaceRead]:
    """List workspaces for the authenticated user."""
    try:
        service = WorkspaceService(db)
        # Only show workspaces owned by the authenticated user
        workspaces = await service.list_workspaces(owner_id=current_user.id)
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Get a workspace by ID. Only accessible by the workspace owner."""
    try:
        service = WorkspaceService(db)
        workspace = await service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        
        # Authorization check: ensure user owns the workspace
        if workspace.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this workspace"
            )
        
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    """Update a workspace. Only accessible by the workspace owner."""
    try:
        service = WorkspaceService(db)
        workspace = await service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        
        # Authorization check: ensure user owns the workspace
        if workspace.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this workspace"
            )
        
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a workspace (cascade deletes all related data). Only accessible by the workspace owner."""
    try:
        service = WorkspaceService(db)
        workspace = await service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        
        # Authorization check: ensure user owns the workspace
        if workspace.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this workspace"
            )
        
        await service.delete_workspace(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting workspace: {str(e)}")

