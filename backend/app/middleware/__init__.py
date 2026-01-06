"""
Middleware Module

Custom middleware for the TayAI application.
"""
from app.middleware.rate_limit import RateLimitMiddleware

__all__ = ["RateLimitMiddleware"]
