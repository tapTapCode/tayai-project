"""
Authentication Endpoints

Provides:
- User login with access and refresh tokens
- Token refresh for extended sessions
- Token verification
- User registration
- Password reset flow
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    generate_password_reset_token,
    verify_password_reset_token,
)
from app.schemas.auth import (
    Token,
    TokenData,
    TokenRefreshRequest,
    UserLogin,
    UserVerify,
    UserCreate,
    UserResponse,
    PasswordChange,
)
from app.services.user_service import UserService
from app.services.membership_service import MembershipService, MembershipPlatform
from app.dependencies import get_current_user
from app.schemas.auth import SSORequest, UserProfile
from app.core.config import settings
import httpx
import logging
import secrets

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def _create_tokens(user) -> Token:
    """Helper to create both access and refresh tokens for a user."""
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "tier": user.tier.value,
            "is_admin": user.is_admin,
        },
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    User login endpoint.
    
    Returns both access token and refresh token for session management.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return _create_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a refresh token.
    
    Returns new access and refresh tokens.
    """
    payload = decode_refresh_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return _create_tokens(user)


@router.post("/verify", response_model=UserVerify)
async def verify_token(token: str = Depends(oauth2_scheme)):
    """Verify JWT token and return user info."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return UserVerify(
        valid=True,
        user_id=payload.get("user_id"),
        username=payload.get("sub"),
        tier=payload.get("tier"),
        is_admin=payload.get("is_admin", False)
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    New users start with the 'basic' tier.
    """
    user_service = UserService(db)
    
    # Check if username exists
    existing_user = await user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    existing_email = await user_service.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await user_service.create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password
    )
    
    return UserResponse.model_validate(user)


@router.post("/password/change")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Change password for authenticated user."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    await user_service.update_password(user.id, password_data.new_password)
    
    return {"message": "Password updated successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current authenticated user's information."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user profile with membership platform data.
    
    Fetches and syncs profile data from the membership platform,
    including course enrollments, profile image, and other metadata.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Try to fetch fresh profile data from membership platform
    profile_data = user.profile_data or {}
    
    if settings.MEMBERSHIP_PLATFORM_API_URL and settings.MEMBERSHIP_PLATFORM_API_KEY:
        try:
            membership_service = MembershipService()
            platform_data = await membership_service.fetch_user_from_platform(user.email)
            
            if platform_data:
                # Update profile data
                profile_data = {
                    "profile_image_url": platform_data.get("avatar_url") or platform_data.get("profile_image"),
                    "full_name": platform_data.get("name") or platform_data.get("full_name"),
                    "enrolled_courses": platform_data.get("courses", []) or platform_data.get("enrollments", []),
                    "membership_start_date": platform_data.get("created_at") or platform_data.get("joined_at"),
                    "last_active": platform_data.get("last_login") or platform_data.get("last_active"),
                    "metadata": {
                        "platform_user_id": platform_data.get("id"),
                        "subscriptions": platform_data.get("subscriptions", []),
                        **platform_data.get("metadata", {})
                    }
                }
                
                # Update user's profile_data in database
                await user_service.update_user(user.id, profile_data=profile_data)
        except Exception as e:
            logger.warning(f"Failed to fetch profile from platform: {e}")
            # Continue with cached profile_data
    
    # Build response
    return UserProfile(
        user_id=user.id,
        email=user.email,
        username=user.username,
        tier=user.tier.value,
        profile_image_url=profile_data.get("profile_image_url"),
        full_name=profile_data.get("full_name"),
        enrolled_courses=profile_data.get("enrolled_courses"),
        membership_start_date=profile_data.get("membership_start_date"),
        last_active=profile_data.get("last_active"),
        metadata=profile_data.get("metadata")
    )


@router.post("/sso", response_model=Token)
async def sso_login(
    sso_request: SSORequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Single Sign-On (SSO) authentication via membership platform.
    
    Accepts a token from the membership platform, verifies it,
    and returns local JWT tokens for seamless authentication.
    
    This enables users to be automatically logged into TayAI when
    they're already authenticated on the membership platform.
    """
    # Validate platform
    try:
        platform_enum = MembershipPlatform(sso_request.platform.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {sso_request.platform}"
        )
    
    membership_service = MembershipService(platform_enum)
    user_service = UserService(db)
    
    # Verify token with platform API
    user_data = None
    if settings.MEMBERSHIP_PLATFORM_API_URL and settings.MEMBERSHIP_PLATFORM_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.MEMBERSHIP_PLATFORM_API_URL}/verify-token",
                    json={"token": sso_request.platform_token},
                    headers={"Authorization": f"Bearer {settings.MEMBERSHIP_PLATFORM_API_KEY}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                else:
                    logger.warning(f"Platform token verification failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to verify platform token: {e}")
    
    # If platform API not available or verification failed, try to extract from token
    # (This is a fallback - in production, always verify with platform)
    if not user_data:
        # For development/testing: accept token as-is if platform API not configured
        if not settings.MEMBERSHIP_PLATFORM_API_URL:
            logger.warning("Platform API not configured - using fallback SSO")
            # Extract email from request or use a default
            email = sso_request.email or f"user_{secrets.token_hex(8)}@example.com"
            user_data = {
                "email": email,
                "name": email.split("@")[0],
                "tier": "basic"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired platform token"
            )
    
    # Extract user info
    email = user_data.get("email") or sso_request.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for SSO"
        )
    
    # Get or create user
    user = await user_service.get_user_by_email(email)
    
    if not user:
        # Create new user from platform data
        username = user_data.get("username") or user_data.get("name", "").replace(" ", "_").lower() or email.split("@")[0]
        
        # Ensure unique username
        if await user_service.get_user_by_username(username):
            username = f"{username}_{secrets.token_hex(4)}"
        
        # Resolve tier from platform data
        tier_str = user_data.get("tier") or user_data.get("product_id") or "basic"
        tier = membership_service.resolve_tier(tier_str)
        
        # Generate random password (user should set via password reset if needed)
        temp_password = secrets.token_urlsafe(16)
        
        user = await user_service.create_user(
            email=email,
            username=username,
            password=temp_password,
            tier=tier
        )
        logger.info(f"Created user via SSO: {email} (tier: {tier.value})")
    else:
        # Update tier if changed on platform
        tier_str = user_data.get("tier") or user_data.get("product_id")
        if tier_str:
            new_tier = membership_service.resolve_tier(tier_str)
            if new_tier != user.tier:
                await user_service.update_user(user.id, tier=new_tier)
                logger.info(f"Updated user tier via SSO: {email} -> {new_tier.value}")
                # Refresh user object
                user = await user_service.get_user_by_id(user.id)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Return local JWT tokens
    return _create_tokens(user)
