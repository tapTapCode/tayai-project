"""
Rate Limit Middleware

Global rate limiting middleware using Redis.
Applies to all API requests with configurable exclusions.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Callable, Set
import json

from app.core.config import settings
from app.core.constants import RATE_LIMIT_EXCLUDED_PATHS
from app.core.rate_limiter import rate_limiter, get_client_ip
from app.core.security import decode_access_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.
    
    Features:
    - IP-based limiting for unauthenticated requests
    - User-based limiting for authenticated requests
    - Tier-based limit multipliers
    - Configurable excluded paths
    """
    
    # Paths excluded from rate limiting
    EXCLUDED_PATHS: Set[str] = set(RATE_LIMIT_EXCLUDED_PATHS)
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Skip for non-API paths
        if not request.url.path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)
        
        # Extract user info from token if present
        user_id = None
        tier = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("user_id")
                tier = payload.get("tier")
        
        # Determine identifier (user_id or IP)
        identifier = str(user_id) if user_id else get_client_ip(request)
        
        # Check rate limit
        allowed, info = rate_limiter.check_rate_limit(identifier, tier)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": info.get("retry_after", 60),
                    "limits": {
                        "minute_limit": info.get("minute_limit"),
                        "minute_remaining": info.get("minute_remaining"),
                        "hour_limit": info.get("hour_limit"),
                        "hour_remaining": info.get("hour_remaining"),
                    }
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(info.get("minute_limit", 60)),
                    "X-RateLimit-Remaining": str(info.get("minute_remaining", 0)),
                }
            )
        
        # Process request and add rate limit headers to response
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(info.get("minute_limit", 60))
        response.headers["X-RateLimit-Remaining"] = str(info.get("minute_remaining", 0))
        
        return response
