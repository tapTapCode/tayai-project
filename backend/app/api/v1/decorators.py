"""
API Decorators

Common decorators for API endpoints to reduce duplication and improve consistency.
"""
from functools import wraps
from typing import Callable, Any
import logging
from fastapi import HTTPException, status
from app.core.exceptions import TayAIError, to_http_exception

logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable) -> Callable:
    """
    Decorator to handle service errors consistently.
    
    Converts TayAIError exceptions to HTTP exceptions automatically.
    
    Usage:
        @handle_service_errors
        async def my_endpoint(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TayAIError as e:
            http_exc = to_http_exception(e)
            raise HTTPException(
                status_code=http_exc.status_code,
                detail=e.to_dict(),
                headers=http_exc.headers
            )
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            )
    
    return wrapper


def validate_input(func: Callable) -> Callable:
    """
    Decorator to validate input parameters.
    
    Can be extended to add common validation logic.
    
    Usage:
        @validate_input
        async def my_endpoint(request: MyRequest):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request object (usually first arg after self/db/current_user)
        for arg in args:
            if hasattr(arg, '__dict__') and hasattr(arg, 'message'):
                # Validate message content if present
                from app.utils.text import validate_message_content
                if hasattr(arg, 'message') and arg.message:
                    is_valid, error_msg = validate_message_content(arg.message)
                    if not is_valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"error": "VALIDATION_ERROR", "message": error_msg}
                        )
                break
        
        return await func(*args, **kwargs)
    
    return wrapper


def log_request(func: Callable) -> Callable:
    """
    Decorator to log API requests.
    
    Usage:
        @log_request
        async def my_endpoint(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"API Request: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"API Success: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"API Error in {func.__name__}: {e}")
            raise
    
    return wrapper
