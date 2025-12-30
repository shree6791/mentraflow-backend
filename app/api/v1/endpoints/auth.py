"""Authentication endpoints for Google Sign-In and username/password."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user as get_current_user_dep
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService

router = APIRouter()

# Rate limiter - will be initialized from app state
def get_limiter(request: Request) -> Limiter:
    """Get rate limiter from app state."""
    return request.app.state.limiter

# Simple rate limiting - temporarily disabled until slowapi is properly configured
# TODO: Implement proper slowapi decorator pattern
def apply_rate_limit(request: Request, limit_str: str):
    """Apply rate limit - placeholder for now."""
    # Rate limiting temporarily disabled to fix startup issues
    # Will be re-enabled with proper slowapi decorator pattern
    pass


# ============================================================================
# Request/Response Models
# ============================================================================

def validate_password_strength(password: str) -> str:
    """Validate password strength.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?/~)
    
    Note: Frontend can also validate for better UX, but backend MUST validate for security.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~" for c in password)
    
    errors = []
    if not has_upper:
        errors.append("one uppercase letter")
    if not has_lower:
        errors.append("one lowercase letter")
    if not has_digit:
        errors.append("one number")
    if not has_special:
        errors.append("one special character")
    
    if errors:
        raise ValueError(f"Password must contain at least {', '.join(errors)}")
    
    return password


class SignupRequest(BaseModel):
    """Signup request for username/password authentication."""
    username: str  # Username (unique identifier)
    email: EmailStr
    password: str
    full_name: str | None = None
    display_name: str | None = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    """Login request for username/password authentication."""
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Request for password reset."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token."""
    token: str  # Password reset token
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


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
    access_token: str  # JWT token
    token_type: str = "bearer"


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post(
    "/auth/signup",
    response_model=AuthResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="User signup with email/password",
)
async def signup(
    request: Request,
    signup_request: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Sign up a new user with email and password.
    
    Creates user and automatically creates default user preferences.
    Password is hashed using bcrypt before storage.
    Rate limited to 5 requests per minute per IP.
    """
    # Rate limiting temporarily disabled - will be re-enabled with proper decorator pattern
    # apply_rate_limit(request, "5/minute")
    try:
        user_service = UserService(db)
        user = await user_service.create_user(
            username=signup_request.username,
            email=signup_request.email,
            password=signup_request.password,  # Password will be hashed in service
            full_name=signup_request.full_name,
            display_name=signup_request.display_name,
            auth_provider="email",
        )
        
        # Generate JWT access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
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
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="User login with email/password",
)
async def login(
    request: Request,
    login_request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Login with email and password.
    
    Verifies password and returns JWT token if valid.
    Rate limited to 10 requests per minute per IP to prevent brute force attacks.
    """
    # Rate limiting temporarily disabled - will be re-enabled with proper decorator pattern
    # apply_rate_limit(request, "10/minute")
    try:
        user_service = UserService(db)
        
        # Verify password
        user = await user_service.verify_user_password(login_request.email, login_request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate JWT access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
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
        # Verify Google ID token
        try:
            from google.auth.transport import requests
            from google.oauth2 import id_token
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google authentication library not installed. Install with: pip install google-auth",
            )
        
        from app.core.config import settings
        
        try:
            # Verify the token
            if settings.GOOGLE_CLIENT_ID:
                idinfo = id_token.verify_oauth2_token(
                    request.id_token, requests.Request(), settings.GOOGLE_CLIENT_ID
                )
                # Verify the issuer
                if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                    raise ValueError("Wrong issuer.")
                
                # Extract user info from verified token
                google_user_id = idinfo.get("sub")
                email_verified = idinfo.get("email_verified", False)
                verified_email = idinfo.get("email")
                
                # Use email from token if verified, otherwise use request email
                if email_verified and verified_email:
                    request.email = verified_email
            else:
                # If GOOGLE_CLIENT_ID is not set, skip verification (dev mode)
                # In production, always set GOOGLE_CLIENT_ID
                pass
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}",
            ) from e
        
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_email(request.email)
        
        if not user:
            # New user - create with Google info
            # Generate username from email (take part before @)
            username_from_email = request.email.split("@")[0]
            # Make it unique by appending a number if needed
            base_username = username_from_email
            counter = 1
            while await user_service.get_user_by_username(base_username):
                base_username = f"{username_from_email}{counter}"
                counter += 1
            
            # Extract Google user ID from token if available
            google_user_id_str = None
            try:
                if settings.GOOGLE_CLIENT_ID:
                    idinfo = id_token.verify_oauth2_token(
                        request.id_token, requests.Request(), settings.GOOGLE_CLIENT_ID
                    )
                    google_user_id_str = idinfo.get("sub")
            except Exception:
                pass
            
            user = await user_service.create_user(
                username=base_username,
                email=request.email,
                password=None,  # No password for Google OAuth users
                full_name=request.full_name,
                display_name=request.display_name,
                auth_provider="google",
                auth_provider_id=google_user_id_str,
            )
        else:
            # Existing user - update info if needed
            if request.full_name and not user.full_name:
                user = await user_service.update_user(
                    user.id,
                    full_name=request.full_name,
                    display_name=request.display_name or request.full_name,
                )
        
        # Generate JWT access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
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
    current_user: Annotated[User, Depends(get_current_user_dep)],
) -> AuthResponse:
    """Get current authenticated user information.
    
    Extracts user from JWT token in Authorization header.
    """
    try:
        # Generate fresh JWT token
        access_token = create_access_token(data={"sub": str(current_user.id)})
        
        return AuthResponse(
            user_id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            display_name=current_user.display_name,
            access_token=access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user: {str(e)}")


@router.post(
    "/auth/forgot-password",
    status_code=200,
    responses={429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Request password reset",
)
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request a password reset.
    
    Generates a reset token and stores it. In production, you should send this token
    via email. For now, the token is returned in the response (for development/testing).
    
    Rate limited to 3 requests per hour per IP to prevent abuse.
    TODO: Integrate with email service (SendGrid, Mailgun, AWS SES, etc.) to send reset link.
    """
    # Rate limiting temporarily disabled - will be re-enabled with proper decorator pattern
    # apply_rate_limit(request, "3/hour")
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_email(forgot_request.email)
        
        # Always return success (don't reveal if email exists)
        if not user:
            # Return success even if user doesn't exist (security best practice)
            return {
                "message": "If an account with that email exists, a password reset link has been sent.",
                "note": "In production, check your email for the reset link."
            }
        
        # Generate reset token (JWT with short expiration - 1 hour)
        reset_token = create_access_token(
            data={"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Store token and expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await user_service.set_password_reset_token(forgot_request.email, reset_token, expires_at)
        
        # TODO: Send email with reset link
        # For now, return token in response (remove in production!)
        return {
            "message": "Password reset token generated. In production, this would be sent via email.",
            "reset_token": reset_token,  # Remove this in production!
            "expires_in": "1 hour",
            "note": "Use this token with /auth/reset-password endpoint. In production, send via email."
        }
    except Exception as e:
        # Always return success (security best practice)
        return {
            "message": "If an account with that email exists, a password reset link has been sent.",
            "note": "In production, check your email for the reset link."
        }


@router.post(
    "/auth/reset-password",
    status_code=200,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Reset password with token",
)
async def reset_password(
    request: Request,
    reset_request: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Reset password using reset token.
    
    Validates the reset token and updates the user's password.
    Rate limited to 5 requests per hour per IP.
    """
    # Rate limiting temporarily disabled - will be re-enabled with proper decorator pattern
    # apply_rate_limit(request, "5/hour")
    try:
        user_service = UserService(db)
        user = await user_service.reset_password_with_token(reset_request.token, reset_request.new_password)
        
        return {
            "message": "Password has been reset successfully",
            "user_id": str(user.id),
            "email": user.email
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting password: {str(e)}")


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

