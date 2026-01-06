"""
Usage service - Business logic for usage tracking and rate limiting
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.db.models import UsageTracking, UserTier, User
from app.core.config import settings
from app.core.exceptions import UsageLimitExceededError
from app.schemas.usage import UsageStatus
from app.services.user_service import UserService
from app.utils.cost_calculator import estimate_cost_from_total_tokens
import redis

# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class UsageService:
    """Service for usage tracking and rate limiting"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_message_limit(self, tier: str) -> int:
        """Get message limit for tier"""
        limits = {
            UserTier.BASIC.value: settings.BASIC_MEMBER_MESSAGES_PER_MONTH,
            UserTier.VIP.value: settings.VIP_MEMBER_MESSAGES_PER_MONTH,
        }
        return limits.get(tier, settings.BASIC_MEMBER_MESSAGES_PER_MONTH)
    
    def _get_upgrade_url(self, tier: str) -> str:
        """Get upgrade URL based on current tier."""
        upgrade_urls = {
            UserTier.BASIC.value: settings.UPGRADE_URL_VIP or settings.UPGRADE_URL_GENERIC,  # Trial -> Elite
            UserTier.VIP.value: settings.UPGRADE_URL_GENERIC,  # Elite has no upgrade
        }
        return upgrade_urls.get(tier, settings.UPGRADE_URL_GENERIC) or ""
    
    async def check_usage_limit(self, user_id: int, tier: str) -> bool:
        """
        Check if user can send a message.
        
        For Basic tier, also checks if trial period is still active.
        
        Raises:
            UsageLimitExceededError: If limit is exceeded or trial expired (includes upgrade URL)
        """
        # Check trial status for Basic tier
        if tier == UserTier.BASIC.value:
            user_service = UserService(self.db)
            trial_status = await user_service.get_trial_status(user_id)
            if not trial_status.get("trial_active", False):
                upgrade_url = self._get_upgrade_url(tier)
                raise UsageLimitExceededError(
                    current_usage=0,
                    limit=0,
                    tier=tier,
                    upgrade_url=upgrade_url,
                    details={
                        "trial_expired": True,
                        "message": "Your 7-day trial has expired. Upgrade to Elite for full access."
                    }
                )
        
        # Get current period
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Check Redis cache first
        cache_key = f"usage:{user_id}:{period_start.strftime('%Y-%m')}"
        cached_count = redis_client.get(cache_key)
        
        if cached_count:
            messages_used = int(cached_count)
        else:
            # Query database
            result = await self.db.execute(
                select(func.sum(UsageTracking.messages_count))
                .where(
                    UsageTracking.user_id == user_id,
                    UsageTracking.period_start >= period_start,
                    UsageTracking.period_end <= period_end
                )
            )
            messages_used = result.scalar() or 0
            # Cache for 1 hour
            redis_client.setex(cache_key, 3600, messages_used)
        
        limit = self._get_message_limit(tier)
        
        if messages_used >= limit:
            upgrade_url = self._get_upgrade_url(tier)
            raise UsageLimitExceededError(
                current_usage=messages_used,
                limit=limit,
                tier=tier,
                upgrade_url=upgrade_url
            )
        
        return True
    
    async def record_usage(self, user_id: int, tokens_used: int = 0):
        """
        Record usage for a user.
        
        Calculates and tracks API costs based on token usage.
        """
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Calculate API cost
        cost_usd = estimate_cost_from_total_tokens(tokens_used)
        cost_micro_dollars = int(cost_usd * 1_000_000)  # Store in micro-dollars for precision
        
        # Get or create usage tracking record
        result = await self.db.execute(
            select(UsageTracking)
            .where(
                UsageTracking.user_id == user_id,
                UsageTracking.period_start == period_start
            )
        )
        usage = result.scalar_one_or_none()
        
        if usage:
            usage.messages_count += 1
            usage.tokens_used += tokens_used
            usage.api_cost += cost_micro_dollars
        else:
            usage = UsageTracking(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                messages_count=1,
                tokens_used=tokens_used,
                api_cost=cost_micro_dollars
            )
            self.db.add(usage)
        
        await self.db.commit()
        
        # Update Redis cache
        cache_key = f"usage:{user_id}:{period_start.strftime('%Y-%m')}"
        redis_client.incr(cache_key)
        redis_client.expire(cache_key, 3600)
    
    async def get_usage_status(self, user_id: int, tier: str) -> UsageStatus:
        """Get current usage status for user"""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        result = await self.db.execute(
            select(UsageTracking)
            .where(
                UsageTracking.user_id == user_id,
                UsageTracking.period_start == period_start
            )
        )
        usage = result.scalar_one_or_none()
        
        messages_used = usage.messages_count if usage else 0
        tokens_used = usage.tokens_used if usage else 0
        api_cost_micro = usage.api_cost if usage else 0
        api_cost_usd = api_cost_micro / 1_000_000 if api_cost_micro else 0.0
        limit = self._get_message_limit(tier)
        
        # Get trial status for Basic tier
        trial_active = None
        trial_days_remaining = None
        trial_end_date = None
        
        if tier == UserTier.BASIC.value:
            user_service = UserService(self.db)
            trial_status = await user_service.get_trial_status(user_id)
            trial_active = trial_status.get("trial_active", False)
            trial_days_remaining = trial_status.get("days_remaining", 0)
            # Get trial_end_date from user object directly
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.trial_end_date:
                trial_end_date = user.trial_end_date
        
        # Check if can send (considering both usage limit and trial status)
        can_send = messages_used < limit
        if tier == UserTier.BASIC.value and not trial_active:
            can_send = False
        
        return UsageStatus(
            user_id=user_id,
            tier=tier,
            messages_used=messages_used,
            messages_limit=limit,
            tokens_used=tokens_used,
            api_cost=round(api_cost_usd, 4),
            period_start=period_start,
            period_end=period_end,
            can_send=can_send,
            trial_active=trial_active,
            trial_days_remaining=trial_days_remaining,
            trial_end_date=trial_end_date
        )
