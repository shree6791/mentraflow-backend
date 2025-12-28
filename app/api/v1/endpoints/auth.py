"""Auth endpoints (stubs - return 501 Not Implemented)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class SignupRequest(BaseModel):
    """Signup request (stub)."""
    email: str
    password: str


class LoginRequest(BaseModel):
    """Login request (stub)."""
    email: str
    password: str


@router.post("/auth/signup", status_code=501, summary="User signup (not implemented)")
async def signup(request: SignupRequest):
    """User signup endpoint - not implemented."""
    raise HTTPException(status_code=501, detail="Authentication not implemented yet")


@router.post("/auth/login", status_code=501, summary="User login (not implemented)")
async def login(request: LoginRequest):
    """User login endpoint - not implemented."""
    raise HTTPException(status_code=501, detail="Authentication not implemented yet")


@router.post("/auth/logout", status_code=501, summary="User logout (not implemented)")
async def logout():
    """User logout endpoint - not implemented."""
    raise HTTPException(status_code=501, detail="Authentication not implemented yet")


@router.get("/auth/me", status_code=501, summary="Get current user (not implemented)")
async def get_current_user():
    """Get current user endpoint - not implemented."""
    raise HTTPException(status_code=501, detail="Authentication not implemented yet")

