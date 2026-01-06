"""
Membership Platform Integration Endpoints

Provides:
- Webhook endpoints for membership platform events
- User tier synchronization
- Platform connection management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.services.membership_service import (
    MembershipService,
    MembershipPlatform,
    MembershipEvent
)
from app.services.user_service import UserService
from app.dependencies import get_current_admin, get_current_user
from app.core.security import get_password_hash
from app.db.models import UserTier
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class WebhookPayload(BaseModel):
    """Generic webhook payload."""
    event_type: Optional[str] = None
    event: Optional[str] = None
    email: Optional[str] = None
    user_email: Optional[str] = None
    name: Optional[str] = None
    user_name: Optional[str] = None
    tier: Optional[str] = None
    product_id: Optional[str] = None
    metadata: Optional[dict] = None
    
    # Platform-specific fields
    user: Optional[dict] = None
    member: Optional[dict] = None
    group: Optional[dict] = None
    community: Optional[dict] = None


class SyncUserRequest(BaseModel):
    """Request to sync a user from membership platform."""
    email: EmailStr
    platform: str = "custom"


class CreateMemberRequest(BaseModel):
    """Request to create/update a member from external platform."""
    email: EmailStr
    username: Optional[str] = None
    tier: str = "basic"
    is_active: bool = True


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/webhook/{platform}")
async def receive_webhook(
    platform: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Receive and process webhooks from membership platforms.
    
    Supported platforms: skool, custom
    
    This endpoint handles:
    - User creation/updates
    - Subscription changes
    - Tier upgrades/downgrades
    
    For Skool integration:
    - Webhook URL: https://your-domain.com/api/v1/membership/webhook/skool
    - Can receive webhooks directly from Skool or via Zapier
    """
    # Validate platform
    try:
        platform_enum = MembershipPlatform(platform.lower())
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported platform: {platform}"
        )
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Initialize service
    membership_service = MembershipService(platform_enum)
    
    # Verify webhook signature (if provided)
    if x_webhook_signature:
        if not membership_service.verify_webhook_signature(body, x_webhook_signature):
            logger.warning(f"Invalid webhook signature from {platform}")
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid webhook signature"
            )
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid JSON payload"
        )
    
    # Parse event
    event_data = membership_service.parse_webhook_event(payload)
    logger.info(f"Received {platform} webhook: {event_data.get('event_type')}")
    
    # Extract user info
    email = event_data.get("user_email")
    if not email:
        logger.warning("Webhook missing user email")
        return {"status": "ignored", "reason": "missing_email"}
    
    user_service = UserService(db)
    
    # Handle event
    event_type = event_data.get("event_type")
    
    if event_type in [MembershipEvent.USER_CREATED, "new_user"]:
        # Create user if doesn't exist
        existing = await user_service.get_user_by_email(email)
        if not existing:
            username = event_data.get("user_name", "").replace(" ", "_").lower() or email.split("@")[0]
            # Generate random password (user should reset)
            temp_password = secrets.token_urlsafe(16)
            
            tier = membership_service.resolve_tier(event_data.get("product_id", "basic"))
            
            await user_service.create_user(
                email=email,
                username=username,
                password=temp_password,
                tier=tier
            )
            logger.info(f"Created user from webhook: {email}")
            return {"status": "created", "email": email, "tier": tier.value}
        
        return {"status": "exists", "email": email}
    
    elif event_type in [
        MembershipEvent.SUBSCRIPTION_CREATED,
        MembershipEvent.SUBSCRIPTION_UPDATED,
        MembershipEvent.PURCHASE_COMPLETED,
        "new_enrollment"
    ]:
        # Update user tier
        user = await user_service.get_user_by_email(email)
        if user:
            new_tier = membership_service.resolve_tier(event_data.get("product_id", "basic"))
            await user_service.update_user(user.id, tier=new_tier)
            logger.info(f"Updated user tier: {email} -> {new_tier.value}")
            return {"status": "updated", "email": email, "tier": new_tier.value}
        
        return {"status": "user_not_found", "email": email}
    
    elif event_type in [MembershipEvent.SUBSCRIPTION_CANCELLED, "enrollment_cancelled"]:
        # Downgrade to basic
        user = await user_service.get_user_by_email(email)
        if user:
            await user_service.update_user(user.id, tier=UserTier.BASIC)
            logger.info(f"Downgraded user: {email} -> basic")
            return {"status": "downgraded", "email": email}
        
        return {"status": "user_not_found", "email": email}
    
    return {"status": "ignored", "event_type": event_type}


# =============================================================================
# Sync Endpoints
# =============================================================================

@router.post("/sync")
async def sync_user_tier(
    request: SyncUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Manually sync a user's tier from membership platform.
    
    Admin only endpoint to force-sync a user's membership status.
    """
    try:
        platform_enum = MembershipPlatform(request.platform.lower())
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported platform: {request.platform}"
        )
    
    membership_service = MembershipService(platform_enum)
    user_service = UserService(db)
    
    # Get user
    user = await user_service.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User not found"
        )
    
    # Sync tier from platform
    new_tier = await membership_service.sync_user_tier(request.email)
    
    if new_tier:
        old_tier = user.tier
        await user_service.update_user(user.id, tier=new_tier)
        
        return {
            "status": "synced",
            "email": request.email,
            "old_tier": old_tier.value,
            "new_tier": new_tier.value
        }
    
    return {
        "status": "no_change",
        "email": request.email,
        "message": "Could not fetch tier from platform"
    }


# =============================================================================
# Member Management (External API)
# =============================================================================

@router.post("/members")
async def create_or_update_member(
    request: CreateMemberRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Create or update a member from external system.
    
    Used for programmatic user management from membership platforms
    or other external systems.
    """
    # Validate tier
    try:
        tier_enum = UserTier(request.tier.lower())
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid tier. Valid: {[t.value for t in UserTier]}"
        )
    
    user_service = UserService(db)
    
    # Check if user exists
    existing = await user_service.get_user_by_email(request.email)
    
    if existing:
        # Update existing user
        await user_service.update_user(
            existing.id,
            tier=tier_enum,
            is_active=request.is_active
        )
        return {
            "status": "updated",
            "user_id": existing.id,
            "email": request.email,
            "tier": tier_enum.value
        }
    
    # Create new user
    username = request.username or request.email.split("@")[0]
    temp_password = secrets.token_urlsafe(16)
    
    # Ensure unique username
    if await user_service.get_user_by_username(username):
        username = f"{username}_{secrets.token_hex(4)}"
    
    user = await user_service.create_user(
        email=request.email,
        username=username,
        password=temp_password,
        tier=tier_enum
    )
    
    return {
        "status": "created",
        "user_id": user.id,
        "email": request.email,
        "username": username,
        "tier": tier_enum.value,
        "temp_password": temp_password  # Only returned on creation
    }


@router.get("/platforms")
async def list_supported_platforms(
    admin: dict = Depends(get_current_admin)
):
    """List supported membership platforms."""
    return {
        "platforms": [
            {"id": p.value, "name": p.name}
            for p in MembershipPlatform
        ]
    }
