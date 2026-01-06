"""
User Service - Business logic for user operations

Provides:
- User CRUD operations
- User lookup by various fields
- Password management
- User statistics
"""
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import User, UserTier
from app.core.security import get_password_hash
from app.core.config import settings
from app.core.constants import (
    MIN_PASSWORD_LENGTH,
    TRIAL_PERIOD_DAYS,
    DEFAULT_PAGE_LIMIT,
)
from app.core.query_helpers import get_paginated_results, count_records
from app.core.performance import optimize_query
from app.core.exceptions import (
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
)
from app.services.base import BaseService
from datetime import datetime, timedelta


class UserService(BaseService[User]):
    """Service for user-related operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, User, "UserService")
    
    # =========================================================================
    # User Lookup Methods
    # =========================================================================
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.get_by_id(user_id)
    
    async def get_user_or_raise(self, user_id: int) -> User:
        """Get user by ID or raise NotFoundError."""
        return await self.get_by_id_or_raise(user_id, "User")
    
    # =========================================================================
    # User CRUD Methods
    # =========================================================================
    
    async def create_user(
        self,
        email: str,
        username: str,
        password: str,
        tier: UserTier = UserTier.BASIC,
        is_admin: bool = False,
        start_trial: bool = True
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User's email address
            username: Unique username
            password: Plain text password (will be hashed)
            tier: Membership tier (defaults to BASIC)
            is_admin: Admin flag (defaults to False)
            
        Returns:
            Created User instance
            
        Raises:
            AlreadyExistsError: If username or email already exists
        """
        # Check for existing username
        if await self.get_user_by_username(username):
            raise AlreadyExistsError("User", "username", username)
        
        # Check for existing email
        if await self.get_user_by_email(email):
            raise AlreadyExistsError("User", "email", email)
        
        # Set trial period for Basic tier
        trial_start = None
        trial_end = None
        if tier == UserTier.BASIC and start_trial:
            trial_start = datetime.utcnow()
            trial_end = trial_start + timedelta(days=TRIAL_PERIOD_DAYS)
        
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            tier=tier,
            is_admin=is_admin,
            is_active=True,
            trial_start_date=trial_start,
            trial_end_date=trial_end
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        self.logger.info(
            f"Created user: {username} (id={user.id}, tier={tier.value}"
            f"{', trial ends: ' + trial_end.isoformat() if trial_end else ''})"
        )
        return user
    
    async def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        username: Optional[str] = None,
        tier: Optional[UserTier] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        profile_data: Optional[dict] = None
    ) -> User:
        """
        Update user fields.
        
        Args:
            user_id: ID of user to update
            **fields: Fields to update
            
        Returns:
            Updated User
            
        Raises:
            NotFoundError: If user not found
            AlreadyExistsError: If new username/email already taken
        """
        user = await self.get_user_or_raise(user_id)
        
        # Check for duplicate username
        if username and username != user.username:
            if await self.get_user_by_username(username):
                raise AlreadyExistsError("User", "username", username)
            user.username = username
        
        # Check for duplicate email
        if email and email != user.email:
            if await self.get_user_by_email(email):
                raise AlreadyExistsError("User", "email", email)
            user.email = email
        
        if tier is not None:
            user.tier = tier
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        if profile_data is not None:
            user.profile_data = profile_data
        
        await self.db.commit()
        await self.db.refresh(user)
        
        self.logger.info(f"Updated user: {user.username} (id={user_id})")
        return user
    
    async def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user's password.
        
        Args:
            user_id: ID of user
            new_password: New plain text password
            
        Returns:
            True if successful
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If password is too short
        """
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
                "password"
            )
        
        user = await self.get_user_or_raise(user_id)
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        self.logger.info(f"Updated password for user: {user.username}")
        return True
    
    async def deactivate_user(self, user_id: int) -> bool:
        """
        Soft delete a user by deactivating.
        
        Args:
            user_id: ID of user to deactivate
            
        Returns:
            True if successful
        """
        user = await self.get_user_or_raise(user_id)
        user.is_active = False
        await self.db.commit()
        
        self.logger.info(f"Deactivated user: {user.username}")
        return True
    
    # =========================================================================
    # User Listing Methods (for Admin)
    # =========================================================================
    
    async def list_users(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
        tier: Optional[UserTier] = None,
        active_only: bool = True
    ) -> List[User]:
        """
        List users with optional filtering.
        
        Args:
            limit: Max users to return
            offset: Pagination offset
            tier: Filter by tier
            active_only: Only return active users
            
        Returns:
            List of User instances
        """
        filters = {}
        if active_only:
            filters["is_active"] = True
        if tier:
            filters["tier"] = tier
        
        return await get_paginated_results(
            self.db,
            User,
            limit=limit,
            offset=offset,
            filters=filters,
            order_by="created_at",
            descending=True
        )
    
    async def get_user_count(self, active_only: bool = True) -> int:
        """Get total user count."""
        filters = {"is_active": True} if active_only else {}
        return await count_records(self.db, User, filters)
    
    async def get_users_by_tier(self) -> Dict[str, int]:
        """Get user counts grouped by tier."""
        result = await self.db.execute(
            select(User.tier, func.count(User.id))
            .where(User.is_active == True)
            .group_by(User.tier)
        )
        return {tier.value: count for tier, count in result.all()}
    
    # =========================================================================
    # Trial Management
    # =========================================================================
    
    async def is_trial_active(self, user_id: int) -> bool:
        """
        Check if user's trial period is still active.
        
        Returns:
            True if trial is active, False otherwise
        """
        user = await self.get_user_by_id(user_id)
        if not user or user.tier != UserTier.BASIC:
            return False
        
        if not user.trial_end_date:
            return False
        
        return datetime.utcnow() < user.trial_end_date
    
    async def get_trial_status(self, user_id: int) -> Dict:
        """
        Get trial status information for a user.
        
        Returns:
            Dict with trial_active, days_remaining, trial_end_date
        """
        user = await self.get_user_by_id(user_id)
        if not user or user.tier != UserTier.BASIC:
            return {
                "trial_active": False,
                "days_remaining": 0,
                "trial_end_date": None
            }
        
        if not user.trial_end_date:
            return {
                "trial_active": False,
                "days_remaining": 0,
                "trial_end_date": None
            }
        
        now = datetime.utcnow()
        trial_active = now < user.trial_end_date
        days_remaining = max(0, (user.trial_end_date - now).days)
        
        return {
            "trial_active": trial_active,
            "days_remaining": days_remaining,
            "trial_end_date": user.trial_end_date.isoformat() if user.trial_end_date else None,
            "trial_start_date": user.trial_start_date.isoformat() if user.trial_start_date else None
        }
