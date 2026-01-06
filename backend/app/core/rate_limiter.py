"""
Redis-based Rate Limiting

Provides:
- Sliding window rate limiting using Redis
- Per-user and per-IP rate limits
- Configurable limits by tier
- Automatic cleanup of expired keys
"""
from datetime import datetime
from typing import Optional, Tuple
import redis
from fastapi import Request, HTTPException, status
from app.core.config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    
    Uses Redis sorted sets to implement a sliding window algorithm
    for accurate rate limiting without burst allowance issues.
    """
    
    def __init__(
        self,
        requests_per_minute: int = settings.RATE_LIMIT_PER_MINUTE,
        requests_per_hour: int = settings.RATE_LIMIT_PER_HOUR
    ):
        self.per_minute = requests_per_minute
        self.per_hour = requests_per_hour
    
    def _get_tier_limits(self, tier: Optional[str]) -> Tuple[int, int]:
        """
        Get rate limits based on user tier.
        
        Args:
            tier: User tier (basic, vip)
            
        Returns:
            Tuple of (per_minute, per_hour) limits
        """
        from app.core.constants import RATE_LIMIT_TIER_MULTIPLIERS
        multiplier = RATE_LIMIT_TIER_MULTIPLIERS.get(tier, 1)
        return (
            self.per_minute * multiplier,
            self.per_hour * multiplier
        )
    
    def _clean_old_requests(self, key: str, window_seconds: int) -> None:
        """Remove requests outside the sliding window."""
        cutoff = datetime.utcnow().timestamp() - window_seconds
        redis_client.zremrangebyscore(key, 0, cutoff)
    
    def _count_requests(self, key: str) -> int:
        """Count requests in the current window."""
        return redis_client.zcard(key) or 0
    
    def _add_request(self, key: str, window_seconds: int) -> None:
        """Add a new request timestamp to the window."""
        now = datetime.utcnow().timestamp()
        redis_client.zadd(key, {f"{now}": now})
        redis_client.expire(key, window_seconds + 1)
    
    def check_rate_limit(
        self,
        identifier: str,
        tier: Optional[str] = None
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limits.
        
        Args:
            identifier: User ID or IP address
            tier: User tier for tier-based limits
            
        Returns:
            Tuple of (allowed: bool, info: dict with remaining/reset times)
        """
        per_minute, per_hour = self._get_tier_limits(tier)
        
        # Keys for different windows
        minute_key = f"rate:{identifier}:minute"
        hour_key = f"rate:{identifier}:hour"
        
        # Clean old requests
        self._clean_old_requests(minute_key, 60)
        self._clean_old_requests(hour_key, 3600)
        
        # Count current requests
        minute_count = self._count_requests(minute_key)
        hour_count = self._count_requests(hour_key)
        
        # Check limits
        minute_remaining = per_minute - minute_count
        hour_remaining = per_hour - hour_count
        
        info = {
            "minute_limit": per_minute,
            "minute_remaining": max(0, minute_remaining),
            "hour_limit": per_hour,
            "hour_remaining": max(0, hour_remaining),
        }
        
        if minute_count >= per_minute:
            info["retry_after"] = 60
            return False, info
        
        if hour_count >= per_hour:
            info["retry_after"] = 3600
            return False, info
        
        # Add this request
        self._add_request(minute_key, 60)
        self._add_request(hour_key, 3600)
        
        return True, info
    
    def get_remaining(self, identifier: str, tier: Optional[str] = None) -> dict:
        """Get remaining requests without consuming a request."""
        per_minute, per_hour = self._get_tier_limits(tier)
        
        minute_key = f"rate:{identifier}:minute"
        hour_key = f"rate:{identifier}:hour"
        
        self._clean_old_requests(minute_key, 60)
        self._clean_old_requests(hour_key, 3600)
        
        return {
            "minute_remaining": max(0, per_minute - self._count_requests(minute_key)),
            "hour_remaining": max(0, per_hour - self._count_requests(hour_key)),
        }


# Singleton instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit_dependency(
    request: Request,
    user_id: Optional[int] = None,
    tier: Optional[str] = None
) -> dict:
    """
    Dependency for rate limiting endpoints.
    
    Can be used with or without authentication.
    Falls back to IP-based limiting for unauthenticated requests.
    
    Raises:
        HTTPException: If rate limit exceeded
        
    Returns:
        Rate limit info dict
    """
    identifier = str(user_id) if user_id else get_client_ip(request)
    
    allowed, info = rate_limiter.check_rate_limit(identifier, tier)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": info.get("retry_after", 60),
                "limits": info
            },
            headers={
                "Retry-After": str(info.get("retry_after", 60)),
                "X-RateLimit-Limit": str(info.get("minute_limit", 60)),
                "X-RateLimit-Remaining": str(info.get("minute_remaining", 0)),
            }
        )
    
    return info
