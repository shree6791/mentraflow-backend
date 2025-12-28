"""FastAPI dependencies for shared resources."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.router import AgentRouter
from app.infrastructure.database import get_db


async def get_agent_router(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentRouter:
    """Dependency to get AgentRouter instance.
    
    Creates a new AgentRouter per request, but the router uses
    a shared GraphRegistry (singleton) that reuses compiled graphs
    across all requests for better performance.
    
    Args:
        db: Database session from get_db dependency
        
    Returns:
        AgentRouter instance for this request
    """
    return AgentRouter(db)

