"""Main API router for v1."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent_runs,
    auth,
    chat,
    documents,
    flashcards,
    kg,
    notes,
    preferences,
    search,
    workspace_members,
    workspaces,
)

api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(workspaces.router, tags=["workspaces"])
api_router.include_router(workspace_members.router, tags=["workspace-members"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(notes.router, tags=["notes"])
api_router.include_router(flashcards.router, tags=["flashcards"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(agent_runs.router, tags=["agent-runs"])
api_router.include_router(preferences.router, tags=["preferences"])
api_router.include_router(kg.router, prefix="/kg", tags=["knowledge-graph"])
api_router.include_router(chat.router, tags=["chat"])

