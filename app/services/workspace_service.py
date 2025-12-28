"""Workspace service."""
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


class WorkspaceService:
    """Service for workspace operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_workspace(
        self,
        owner_user_id: uuid.UUID,
        name: str,
        plan_tier: str | None = None,
    ) -> Workspace:
        """Create a new workspace and automatically add owner as workspace member.
        
        When a workspace is created, the owner is automatically added as a workspace
        member with role="owner" and status="active".
        """
        try:
            workspace = Workspace(
                owner_user_id=owner_user_id,
                name=name,
                plan_tier=plan_tier,
            )
            self.db.add(workspace)
            await self.db.flush()  # Flush to get workspace.id before commit
            
            # Automatically add owner as workspace member
            from app.models.workspace_membership import WorkspaceMembership
            membership = WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=owner_user_id,
                role="owner",
                status="active",
            )
            self.db.add(membership)
            
            await self.db.commit()
            await self.db.refresh(workspace)
            return workspace
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while creating workspace: {str(e)}") from e

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Get a workspace by ID."""
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_workspaces(self, owner_user_id: uuid.UUID | None = None) -> list[Workspace]:
        """List workspaces, optionally filtered by owner."""
        stmt = select(Workspace)
        if owner_user_id:
            stmt = stmt.where(Workspace.owner_user_id == owner_user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        name: str | None = None,
        plan_tier: str | None = None,
    ) -> Workspace:
        """Update a workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        try:
            if name is not None:
                workspace.name = name
            if plan_tier is not None:
                workspace.plan_tier = plan_tier
            await self.db.commit()
            await self.db.refresh(workspace)
            return workspace
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while updating workspace: {str(e)}") from e

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        """Delete a workspace (cascade deletes all related data)."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        try:
            await self.db.delete(workspace)
            await self.db.commit()
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Database error while deleting workspace: {str(e)}") from e

