"""Workspace membership endpoints (optional)."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse

router = APIRouter()


class WorkspaceMemberRead(BaseModel):
    """Schema for reading a workspace member."""
    workspace_id: uuid.UUID = Field(description="Workspace ID")
    user_id: uuid.UUID = Field(description="User ID")
    role: str | None = Field(description="Member role")
    status: str | None = Field(description="Membership status")
    created_at: str = Field(description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    """Request body for adding a workspace member."""
    user_id: uuid.UUID = Field(description="User ID to add")
    role: str = Field(default="member", description="Member role (owner, admin, member)")
    status: str = Field(default="active", description="Membership status")


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Add a workspace member",
)
async def add_workspace_member(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    request: AddMemberRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMemberRead:
    """Add a member to a workspace."""
    try:
        from sqlalchemy.exc import SQLAlchemyError
        from app.models.workspace_membership import WorkspaceMembership
        
        # Check if membership already exists
        from sqlalchemy import select
        stmt = select(WorkspaceMembership).where(
            (WorkspaceMembership.workspace_id == workspace_id) &
            (WorkspaceMembership.user_id == request.user_id)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(status_code=400, detail="User is already a member of this workspace")
        
        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=request.user_id,
            role=request.role,
            status=request.status,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)
        return WorkspaceMemberRead.model_validate(membership)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding member: {str(e)}")


@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=list[WorkspaceMemberRead],
    responses={500: {"model": ErrorResponse}},
    summary="List workspace members",
)
async def list_workspace_members(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[WorkspaceMemberRead]:
    """List all members of a workspace."""
    try:
        from sqlalchemy import select
        from app.models.workspace_membership import WorkspaceMembership
        
        stmt = select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id)
        result = await db.execute(stmt)
        members = list(result.scalars().all())
        return [WorkspaceMemberRead.model_validate(m) for m in members]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing members: {str(e)}")


@router.delete(
    "/workspaces/{workspace_id}/members/{member_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Remove a workspace member",
)
async def remove_workspace_member(
    workspace_id: Annotated[uuid.UUID, Path(description="Workspace ID")],
    member_id: Annotated[uuid.UUID, Path(description="Membership ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a member from a workspace."""
    try:
        from sqlalchemy import select
        from app.models.workspace_membership import WorkspaceMembership
        
        stmt = select(WorkspaceMembership).where(
            (WorkspaceMembership.id == member_id) &
            (WorkspaceMembership.workspace_id == workspace_id)
        )
        result = await db.execute(stmt)
        membership = result.scalar_one_or_none()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Membership not found")
        
        await db.delete(membership)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing member: {str(e)}")

