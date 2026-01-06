"""
Performance Optimization Utilities

Provides caching, query optimization, and performance monitoring.
"""
import functools
import time
import logging
from typing import Any, Callable, Optional
from functools import wraps
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Redis client for caching
try:
    cache_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    logger.warning(f"Redis cache not available: {e}")
    cache_client = None


def cache_result(ttl: int = 3600, key_prefix: str = "cache"):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        key_prefix: Prefix for cache key
    
    Usage:
        @cache_result(ttl=1800, key_prefix="user")
        async def get_user(user_id: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            if cache_client:
                try:
                    cached = cache_client.get(cache_key)
                    if cached:
                        import json
                        return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if cache_client and result is not None:
                try:
                    import json
                    cache_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator


def cache_result_sync(ttl: int = 3600, key_prefix: str = "cache"):
    """Synchronous version of cache_result decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            
            if cache_client:
                try:
                    cached = cache_client.get(cache_key)
                    if cached:
                        import json
                        return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")
            
            result = func(*args, **kwargs)
            
            if cache_client and result is not None:
                try:
                    import json
                    cache_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator


def measure_performance(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Logs execution time for performance monitoring.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to ms
            logger.info(
                f"{func.__name__} executed in {duration:.2f}ms"
            )
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = (time.time() - start_time) * 1000
            logger.info(
                f"{func.__name__} executed in {duration:.2f}ms"
            )
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def optimize_query(query, limit: Optional[int] = None, offset: int = 0):
    """
    Optimize SQLAlchemy query with pagination and limits.
    
    Args:
        query: SQLAlchemy query object
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        Optimized query
    """
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    
    return query


def batch_process(items: list, batch_size: int = 100, func: Callable = None):
    """
    Process items in batches for better performance.
    
    Args:
        items: List of items to process
        batch_size: Number of items per batch
        func: Optional function to apply to each batch
    
    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        if func:
            yield func(batch)
        else:
            yield batch


def clear_cache(pattern: str = "*"):
    """
    Clear cache entries matching pattern.
    
    Args:
        pattern: Redis key pattern (default: all)
    """
    if cache_client:
        try:
            keys = cache_client.keys(pattern)
            if keys:
                cache_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
