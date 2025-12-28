"""Authentication endpoints for Google Sign-In and username/password."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SignupRequest(BaseModel):
    """Signup request for username/password authentication."""
    username: str  # Username (unique identifier)
    email: EmailStr
    password: str
    full_name: str | None = None
    display_name: str | None = None


class LoginRequest(BaseModel):
    """Login request for username/password authentication."""
    email: EmailStr
    password: str


class GoogleSignInRequest(BaseModel):
    """Google Sign-In request."""
    id_token: str  # Google ID token from frontend
    email: EmailStr
    full_name: str | None = None
    display_name: str | None = None


class AuthResponse(BaseModel):
    """Authentication response."""
    user_id: uuid.UUID
    username: str
    email: str
    full_name: str | None
    display_name: str | None
    access_token: str  # JWT token (to be implemented)
    token_type: str = "bearer"


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post(
    "/auth/signup",
    response_model=AuthResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="User signup with email/password",
)
async def signup(
    request: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Sign up a new user with email and password.
    
    Creates user and automatically creates default user preferences.
    """
    try:
        # TODO: Hash password (use bcrypt or similar)
        # TODO: Validate password strength
        
        user_service = UserService(db)
        user = await user_service.create_user(
            username=request.username,
            email=request.email,
            full_name=request.full_name,
            display_name=request.display_name,
            auth_provider="email",
        )
        
        # TODO: Generate JWT access token
        # For now, return placeholder
        access_token = "placeholder_token"  # Replace with actual JWT
        
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            access_token=access_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during signup: {str(e)}")


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="User login with email/password",
)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Login with email and password.
    
    If user doesn't exist, creates user automatically (first-time login).
    """
    try:
        user_service = UserService(db)
        
        # Try to find existing user
        user = await user_service.get_user_by_email(request.email)
        
        if not user:
            # First-time login - create user automatically
            # Generate username from email (take part before @)
            username_from_email = request.email.split("@")[0]
            # Make it unique by appending a number if needed
            base_username = username_from_email
            counter = 1
            while await user_service.get_user_by_username(base_username):
                base_username = f"{username_from_email}{counter}"
                counter += 1
            
            user = await user_service.create_user(
                username=base_username,
                email=request.email,
                auth_provider="email",
            )
        
        # TODO: Verify password (use bcrypt or similar)
        # TODO: Generate JWT access token
        # For now, return placeholder
        access_token = "placeholder_token"  # Replace with actual JWT
        
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            access_token=access_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during login: {str(e)}")


@router.post(
    "/auth/google",
    response_model=AuthResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Google Sign-In authentication",
)
async def google_signin(
    request: GoogleSignInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate with Google Sign-In.
    
    Verifies Google ID token and creates/updates user.
    Automatically creates default user preferences for new users.
    """
    try:
        # TODO: Verify Google ID token using google-auth library
        # from google.auth import verify_id_token
        # user_info = verify_id_token(request.id_token)
        
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_email(request.email)
        
        if not user:
            # New user - create with Google info
            # Generate username from email (take part before @)
            username_from_email = request.email.split("@")[0]
            # Make it unique by appending a number if needed (simple approach)
            base_username = username_from_email
            counter = 1
            while await user_service.get_user_by_username(base_username):
                base_username = f"{username_from_email}{counter}"
                counter += 1
            
            user = await user_service.create_user(
                username=base_username,
                email=request.email,
                full_name=request.full_name,
                display_name=request.display_name,
                auth_provider="google",
                auth_provider_id=request.id_token,  # TODO: Extract actual Google user ID
            )
        else:
            # Existing user - update info if needed
            if request.full_name and not user.full_name:
                user = await user_service.update_user(
                    user.id,
                    full_name=request.full_name,
                    display_name=request.display_name or request.full_name,
                )
        
        # TODO: Generate JWT access token
        # For now, return placeholder
        access_token = "placeholder_token"  # Replace with actual JWT
        
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            access_token=access_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during Google sign-in: {str(e)}")


@router.post(
    "/auth/logout",
    status_code=200,
    summary="User logout",
)
async def logout():
    """Logout endpoint.
    
    Note: With JWT tokens, logout is typically handled client-side by
    removing the token. Server-side token blacklisting can be added if needed.
    """
    return {"message": "Logged out successfully"}


@router.get(
    "/auth/me",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get current authenticated user",
)
async def get_current_user(
    user_id: Annotated[uuid.UUID, Query(description="User ID")],  # TODO: Get from JWT token
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Get current authenticated user information.
    
    TODO: Extract user_id from JWT token instead of query parameter.
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # TODO: Generate fresh JWT token
        access_token = "placeholder_token"  # Replace with actual JWT
        
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            access_token=access_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user: {str(e)}")


@router.get(
    "/users/by-username/{username}",
    response_model=AuthResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get user by username",
)
async def get_user_by_username(
    username: Annotated[str, Path(description="Username to look up")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Get user information by username.
    
    Useful for looking up user_id when you only have the username.
    Returns user information including user_id, which can be used for document creation, etc.
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_username(username)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with username '{username}' not found",
            )
        
        # Return user info (no token needed for lookup)
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            access_token="",  # Not needed for lookup
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up user: {str(e)}")

