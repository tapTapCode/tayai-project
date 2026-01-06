"""
Role-Based Access Control (RBAC) System

Provides:
- Permission definitions for all system actions
- Role definitions with assigned permissions
- Permission checking utilities and dependencies
- Tier-based permission modifiers

This implements a flexible RBAC system where:
- Permissions define specific actions
- Roles group permissions together
- Tiers modify what features are available
"""
from enum import Enum, auto
from typing import Set, Optional, List
from functools import wraps
from fastapi import HTTPException, status, Depends

from app.db.models import UserTier


# =============================================================================
# Permission Definitions
# =============================================================================

class Permission(str, Enum):
    """
    System permissions.
    
    Naming convention: RESOURCE_ACTION
    """
    # Chat permissions
    CHAT_SEND = "chat:send"
    CHAT_STREAM = "chat:stream"
    CHAT_HISTORY_READ = "chat:history:read"
    CHAT_HISTORY_DELETE = "chat:history:delete"
    
    # Knowledge Base permissions (admin)
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_CREATE = "knowledge:create"
    KNOWLEDGE_UPDATE = "knowledge:update"
    KNOWLEDGE_DELETE = "knowledge:delete"
    KNOWLEDGE_BULK = "knowledge:bulk"
    KNOWLEDGE_REINDEX = "knowledge:reindex"
    
    # User management permissions (admin)
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_CREATE = "users:create"
    
    # System permissions (admin)
    SYSTEM_STATS = "system:stats"
    SYSTEM_MONITOR = "system:monitor"
    
    # Membership permissions (admin)
    MEMBERSHIP_SYNC = "membership:sync"
    MEMBERSHIP_WEBHOOK = "membership:webhook"
    
    # Persona testing (admin)
    PERSONA_TEST = "persona:test"


# =============================================================================
# Role Definitions
# =============================================================================

class Role(str, Enum):
    """
    User roles in the system.
    
    Hierarchy: SUPER_ADMIN > ADMIN > MODERATOR > USER > GUEST
    """
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Role -> Permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.GUEST: set(),  # No permissions
    
    Role.USER: {
        Permission.CHAT_SEND,
        Permission.CHAT_STREAM,
        Permission.CHAT_HISTORY_READ,
        Permission.CHAT_HISTORY_DELETE,
    },
    
    Role.MODERATOR: {
        # User permissions
        Permission.CHAT_SEND,
        Permission.CHAT_STREAM,
        Permission.CHAT_HISTORY_READ,
        Permission.CHAT_HISTORY_DELETE,
        # Knowledge read-only
        Permission.KNOWLEDGE_READ,
        # User viewing
        Permission.USERS_READ,
    },
    
    Role.ADMIN: {
        # All user permissions
        Permission.CHAT_SEND,
        Permission.CHAT_STREAM,
        Permission.CHAT_HISTORY_READ,
        Permission.CHAT_HISTORY_DELETE,
        # Knowledge management
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_CREATE,
        Permission.KNOWLEDGE_UPDATE,
        Permission.KNOWLEDGE_DELETE,
        Permission.KNOWLEDGE_BULK,
        # User management
        Permission.USERS_READ,
        Permission.USERS_UPDATE,
        # System
        Permission.SYSTEM_STATS,
        Permission.SYSTEM_MONITOR,
        # Persona testing
        Permission.PERSONA_TEST,
        # Membership
        Permission.MEMBERSHIP_SYNC,
    },
    
    Role.SUPER_ADMIN: {
        # All permissions
        Permission.CHAT_SEND,
        Permission.CHAT_STREAM,
        Permission.CHAT_HISTORY_READ,
        Permission.CHAT_HISTORY_DELETE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_CREATE,
        Permission.KNOWLEDGE_UPDATE,
        Permission.KNOWLEDGE_DELETE,
        Permission.KNOWLEDGE_BULK,
        Permission.KNOWLEDGE_REINDEX,
        Permission.USERS_READ,
        Permission.USERS_UPDATE,
        Permission.USERS_DELETE,
        Permission.USERS_CREATE,
        Permission.SYSTEM_STATS,
        Permission.SYSTEM_MONITOR,
        Permission.MEMBERSHIP_SYNC,
        Permission.MEMBERSHIP_WEBHOOK,
        Permission.PERSONA_TEST,
    },
}


# =============================================================================
# Tier-Based Feature Access
# =============================================================================

# Features available per tier (beyond base permissions)
TIER_FEATURES: dict[UserTier, Set[str]] = {
    UserTier.BASIC: {
        "chat_basic",
        "hair_education",
    },
    UserTier.VIP: {
        "chat_basic",
        "chat_streaming",
        "chat_priority",
        "hair_education",
        "business_mentorship",
        "product_recommendations",
        "troubleshooting",
        "exclusive_content",
    },
}


# =============================================================================
# Permission Checking Utilities
# =============================================================================

def get_role_from_user(user: dict) -> Role:
    """
    Determine user's role from user data.
    
    Args:
        user: User data dict from authentication
        
    Returns:
        User's Role
    """
    if user.get("is_super_admin"):
        return Role.SUPER_ADMIN
    elif user.get("is_admin"):
        return Role.ADMIN
    elif user.get("is_moderator"):
        return Role.MODERATOR
    elif user.get("user_id"):
        return Role.USER
    return Role.GUEST


def has_permission(user: dict, permission: Permission) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user: User data dict
        permission: Permission to check
        
    Returns:
        True if user has permission
    """
    role = get_role_from_user(user)
    role_perms = ROLE_PERMISSIONS.get(role, set())
    return permission in role_perms


def has_any_permission(user: dict, permissions: List[Permission]) -> bool:
    """Check if user has any of the given permissions."""
    return any(has_permission(user, p) for p in permissions)


def has_all_permissions(user: dict, permissions: List[Permission]) -> bool:
    """Check if user has all of the given permissions."""
    return all(has_permission(user, p) for p in permissions)


def has_feature(tier: UserTier, feature: str) -> bool:
    """
    Check if a tier has access to a specific feature.
    
    Args:
        tier: User's membership tier
        feature: Feature to check
        
    Returns:
        True if tier has feature access
    """
    tier_features = TIER_FEATURES.get(tier, set())
    return feature in tier_features


# =============================================================================
# FastAPI Dependencies
# =============================================================================

def require_permission(permission: Permission):
    """
    Create a dependency that requires a specific permission.
    
    Usage:
        @router.get("/items")
        async def list_items(
            user: dict = Depends(require_permission(Permission.ITEMS_READ))
        ):
            ...
    """
    from app.dependencies import get_current_user
    
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        return current_user
    
    return permission_checker


def require_any_permission(*permissions: Permission):
    """
    Create a dependency that requires any of the specified permissions.
    """
    from app.dependencies import get_current_user
    
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if not has_any_permission(current_user, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user
    
    return permission_checker


def require_feature(feature: str):
    """
    Create a dependency that requires a specific tier feature.
    
    Usage:
        @router.post("/advanced")
        async def advanced_feature(
            user: dict = Depends(require_feature("business_mentorship"))
        ):
            ...
    """
    from app.dependencies import get_current_user
    
    async def feature_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        tier_str = current_user.get("tier", "basic")
        try:
            tier = UserTier(tier_str)
        except ValueError:
            tier = UserTier.BASIC
        
        if not has_feature(tier, feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature not available in your membership tier: {feature}"
            )
        return current_user
    
    return feature_checker


def require_role(minimum_role: Role):
    """
    Create a dependency that requires at least a specific role level.
    
    Role hierarchy: GUEST < USER < MODERATOR < ADMIN < SUPER_ADMIN
    """
    from app.dependencies import get_current_user
    
    role_hierarchy = {
        Role.GUEST: 0,
        Role.USER: 1,
        Role.MODERATOR: 2,
        Role.ADMIN: 3,
        Role.SUPER_ADMIN: 4,
    }
    
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_role = get_role_from_user(current_user)
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(minimum_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Minimum role required: {minimum_role.value}"
            )
        return current_user
    
    return role_checker


# =============================================================================
# Permission Decorators (Alternative API)
# =============================================================================

def permission_required(permission: Permission):
    """
    Decorator for requiring a permission on a function.
    
    Usage:
        @permission_required(Permission.ITEMS_CREATE)
        async def create_item(request, user):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: dict = None, **kwargs):
            if user and not has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
