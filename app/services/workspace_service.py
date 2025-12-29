"""Workspace service."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.services.base import BaseService


class WorkspaceService(BaseService):
    """Service for workspace operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        super().__init__(db)

    async def create_workspace(
        self,
        owner_id: uuid.UUID,
        name: str,
        plan_tier: str | None = None,
    ) -> Workspace:
        """Create a new workspace and automatically add owner as workspace member.
        
        When a workspace is created, the owner is automatically added as a workspace
        member with role="owner" and status="active".
        """
        workspace = Workspace(
            owner_id=owner_id,
            name=name,
            plan_tier=plan_tier,
        )
        self.db.add(workspace)
        await self.db.flush()  # Flush to get workspace.id before commit
        
        # Automatically add owner as workspace member
        from app.models.workspace_membership import WorkspaceMembership
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=owner_id,
            role="owner",
            status="active",
        )
        self.db.add(membership)
        
        await self._commit_and_refresh(workspace)
        return workspace

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Get a workspace by ID."""
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_workspaces(self, owner_id: uuid.UUID | None = None) -> list[Workspace]:
        """List workspaces, optionally filtered by owner."""
        stmt = select(Workspace)
        if owner_id:
            stmt = stmt.where(Workspace.owner_id == owner_id)
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
        
        if name is not None:
            workspace.name = name
        if plan_tier is not None:
            workspace.plan_tier = plan_tier
        await self._commit_and_refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        """Delete a workspace (cascade deletes all related data)."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        await self.db.delete(workspace)
        await self.db.commit()

