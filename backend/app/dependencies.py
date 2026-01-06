"""
Dependencies for FastAPI Endpoints

Provides authentication and authorization dependencies:
- get_current_user: Returns authenticated user data
- get_current_admin: Requires admin role
- get_optional_user: Returns user if authenticated, None otherwise
- Permission-based dependencies (from core.permissions)
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import decode_access_token
from app.services.user_service import UserService

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency to get current authenticated user.
    
    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 404: If user not found
        HTTPException 403: If user account is inactive
        
    Returns:
        Dict with user data including permissions info
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Build comprehensive user context
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "tier": user.tier.value,
        "is_admin": user.is_admin,
        "is_moderator": getattr(user, "is_moderator", False),
        "is_super_admin": getattr(user, "is_super_admin", False),
        "is_active": user.is_active,
    }


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """
    Dependency to optionally get current user.
    
    Returns user data if authenticated, None otherwise.
    Does not raise exceptions for missing/invalid tokens.
    """
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if user is None or not user.is_active:
        return None
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "tier": user.tier.value,
        "is_admin": user.is_admin,
        "is_moderator": getattr(user, "is_moderator", False),
        "is_super_admin": getattr(user, "is_super_admin", False),
        "is_active": user.is_active,
    }


async def get_current_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to require admin access.
    
    Raises:
        HTTPException 403: If user is not an admin
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_super_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to require super admin access.
    
    Raises:
        HTTPException 403: If user is not a super admin
    """
    if not current_user.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_current_moderator(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to require at least moderator access.
    
    Accepts moderator, admin, or super_admin.
    
    Raises:
        HTTPException 403: If user is not a moderator or higher
    """
    is_mod_or_higher = (
        current_user.get("is_moderator") or
        current_user.get("is_admin") or
        current_user.get("is_super_admin")
    )
    if not is_mod_or_higher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required"
        )
    return current_user
