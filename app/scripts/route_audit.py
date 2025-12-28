#!/usr/bin/env python3
"""Route audit script.

Compares existing FastAPI routes against the MentraFlow v1 route contract.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.routing import APIRoute
from app.main import app


# Route contract from requirements
ROUTE_CONTRACT = {
    # Health/Meta
    ("GET", "/health"): "Health check",
    ("GET", "/v1/version"): "API version",
    
    # Auth (stubs - return 501)
    ("POST", "/v1/auth/signup"): "User signup",
    ("POST", "/v1/auth/login"): "User login",
    ("POST", "/v1/auth/logout"): "User logout",
    ("GET", "/v1/auth/me"): "Get current user",
    
    # Workspaces
    ("POST", "/v1/workspaces"): "Create workspace",
    ("GET", "/v1/workspaces"): "List workspaces",
    ("GET", "/v1/workspaces/{workspace_id}"): "Get workspace",
    ("PATCH", "/v1/workspaces/{workspace_id}"): "Update workspace",
    ("DELETE", "/v1/workspaces/{workspace_id}"): "Delete workspace",
    
    # Workspace Members (optional)
    ("POST", "/v1/workspaces/{workspace_id}/members"): "Add member",
    ("GET", "/v1/workspaces/{workspace_id}/members"): "List members",
    ("DELETE", "/v1/workspaces/{workspace_id}/members/{member_id}"): "Remove member",
    
    # Documents
    ("POST", "/v1/workspaces/{workspace_id}/documents"): "Create document (workspace-scoped)",
    ("GET", "/v1/workspaces/{workspace_id}/documents"): "List documents",
    ("GET", "/v1/documents/{document_id}"): "Get document",
    ("PATCH", "/v1/documents/{document_id}"): "Update document",
    ("DELETE", "/v1/documents/{document_id}"): "Delete document",
    
    # Ingestion
    ("POST", "/v1/documents/{document_id}/ingest"): "Ingest document",
    ("GET", "/v1/documents/{document_id}/status"): "Get document status",
    
    # Summary
    ("GET", "/v1/documents/{document_id}/summary"): "Get document summary",
    ("POST", "/v1/documents/{document_id}/summary"): "Regenerate summary",
    
    # Chat
    ("POST", "/v1/chat"): "Chat with study assistant",
    
    # Notes
    ("POST", "/v1/notes"): "Create note",
    ("GET", "/v1/notes"): "List notes",
    ("GET", "/v1/notes/{note_id}"): "Get note",
    ("PATCH", "/v1/notes/{note_id}"): "Update note",
    ("DELETE", "/v1/notes/{note_id}"): "Delete note",
    
    # Flashcards
    ("POST", "/v1/documents/{document_id}/flashcards"): "Generate flashcards",
    ("GET", "/v1/flashcards"): "List flashcards",
    ("GET", "/v1/flashcards/{flashcard_id}"): "Get flashcard",
    ("GET", "/v1/flashcards/due"): "Get due flashcards",
    ("POST", "/v1/flashcards/{flashcard_id}/review"): "Review flashcard",
    
    # Knowledge Graph (v1.5)
    ("POST", "/v1/documents/{document_id}/kg"): "Extract KG",
    ("GET", "/v1/concepts"): "List concepts",
    ("GET", "/v1/concepts/{concept_id}"): "Get concept",
    ("GET", "/v1/concepts/{concept_id}/neighbors"): "Get concept neighbors",
    ("GET", "/v1/edges"): "List edges",
    
    # Search
    ("POST", "/v1/search"): "Semantic search",
    
    # Agent Runs
    ("GET", "/v1/agent-runs/{run_id}"): "Get agent run",
    ("GET", "/v1/agent-runs"): "List agent runs",
    
    # Preferences
    ("GET", "/v1/preferences"): "Get preferences",
    ("PATCH", "/v1/preferences"): "Update preferences",
}


def normalize_path(path: str) -> str:
    """Normalize path for comparison."""
    # Remove trailing slashes
    path = path.rstrip("/")
    # Normalize path parameters (e.g., {workspace_id} vs <workspace_id>)
    import re
    path = re.sub(r"\{[^}]+\}", "{param}", path)
    return path


def get_existing_routes(app: FastAPI) -> dict[tuple[str, str], str]:
    """Extract all routes from FastAPI app."""
    routes = {}
    
    def extract_routes(route, prefix=""):
        if isinstance(route, APIRoute):
            method = route.methods.pop() if route.methods else "GET"
            path = normalize_path(prefix + route.path)
            routes[(method, path)] = route.summary or route.name or "No description"
        elif hasattr(route, "routes"):
            # Nested router
            for sub_route in route.routes:
                extract_routes(sub_route, prefix + (route.prefix or ""))
    
    for route in app.routes:
        extract_routes(route, "")
    
    return routes


def audit_routes():
    """Compare existing routes against contract."""
    existing = get_existing_routes(app)
    contract_paths = {normalize_path(path): (method, desc) for (method, path), desc in ROUTE_CONTRACT.items()}
    
    print("=" * 80)
    print("MENTRAFLOW ROUTE AUDIT")
    print("=" * 80)
    print()
    
    # Find missing routes
    missing = []
    for (method, path), desc in ROUTE_CONTRACT.items():
        normalized = normalize_path(path)
        if (method, normalized) not in existing:
            missing.append((method, path, desc))
    
    # Find extra routes (not in contract)
    extra = []
    for (method, path), desc in existing.items():
        # Check if this matches any contract route
        found = False
        for (c_method, c_path), _ in ROUTE_CONTRACT.items():
            if method == c_method and normalize_path(c_path) == path:
                found = True
                break
        if not found:
            extra.append((method, path, desc))
    
    print(f"✅ Existing routes: {len(existing)}")
    print(f"📋 Contract routes: {len(ROUTE_CONTRACT)}")
    print(f"❌ Missing routes: {len(missing)}")
    print(f"➕ Extra routes: {len(extra)}")
    print()
    
    if missing:
        print("MISSING ROUTES:")
        print("-" * 80)
        for method, path, desc in sorted(missing):
            print(f"  {method:6} {path:50} - {desc}")
        print()
    
    if extra:
        print("EXTRA ROUTES (not in contract):")
        print("-" * 80)
        for method, path, desc in sorted(extra):
            print(f"  {method:6} {path:50} - {desc}")
        print()
    
    if existing:
        print("EXISTING ROUTES:")
        print("-" * 80)
        for (method, path), desc in sorted(existing.items()):
            print(f"  {method:6} {path:50} - {desc}")
        print()
    
    # Return exit code
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(audit_routes())

