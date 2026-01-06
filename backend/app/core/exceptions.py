"""
Custom Exceptions for TayAI

Provides a hierarchy of custom exceptions for consistent error handling
across the application. All exceptions include error codes for API responses.

Usage:
    from app.core.exceptions import NotFoundError, ValidationError
    
    raise NotFoundError("User", user_id)
    raise ValidationError("Invalid email format")
"""
from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class TayAIError(Exception):
    """
    Base exception for all TayAI errors.
    
    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error details
    """
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Resource Errors (4xx)
# =============================================================================

class NotFoundError(TayAIError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource: str,
        identifier: Any = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if identifier is not None:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier, **(details or {})}
        )


class AlreadyExistsError(TayAIError):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(
        self,
        resource: str,
        field: str,
        value: Any,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            code="ALREADY_EXISTS",
            details={"resource": resource, "field": field, "value": value, **(details or {})}
        )


class ValidationError(TayAIError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})} if field else details
        )


# =============================================================================
# Authentication & Authorization Errors
# =============================================================================

class AuthenticationError(TayAIError):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""
    
    def __init__(self):
        super().__init__(
            message="Invalid username or password",
            details={"hint": "Check your credentials and try again"}
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""
    
    def __init__(self):
        super().__init__(
            message="Token has expired",
            details={"hint": "Please login again or refresh your token"}
        )


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""
    
    def __init__(self):
        super().__init__(
            message="Invalid token",
            details={"hint": "Token is malformed or has been tampered with"}
        )


class PermissionDeniedError(TayAIError):
    """Raised when user lacks permission for an action."""
    
    def __init__(
        self,
        action: str = "perform this action",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Permission denied to {action}"
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            details={
                "required_permission": required_permission,
                **(details or {})
            }
        )


class InactiveUserError(TayAIError):
    """Raised when an inactive user attempts to authenticate."""
    
    def __init__(self):
        super().__init__(
            message="User account is inactive",
            code="INACTIVE_USER",
            details={"hint": "Contact support to reactivate your account"}
        )


# =============================================================================
# Rate Limiting & Usage Errors
# =============================================================================

class RateLimitExceededError(TayAIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        retry_after: int = 60,
        limit_type: str = "requests",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Rate limit exceeded for {limit_type}",
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after, "limit_type": limit_type, **(details or {})}
        )
        self.retry_after = retry_after


class UsageLimitExceededError(TayAIError):
    """Raised when usage limit is exceeded."""
    
    def __init__(
        self,
        current_usage: int,
        limit: int,
        tier: str,
        upgrade_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message="Monthly message limit exceeded",
            code="USAGE_LIMIT_EXCEEDED",
            details={
                "current_usage": current_usage,
                "limit": limit,
                "tier": tier,
                "upgrade_url": upgrade_url,
                "hint": "Upgrade your membership for more messages",
                **(details or {})
            }
        )


# =============================================================================
# External Service Errors
# =============================================================================

class ExternalServiceError(TayAIError):
    """Raised when an external service fails."""
    
    def __init__(
        self,
        service: str,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})}
        )


class OpenAIError(ExternalServiceError):
    """Raised when OpenAI API fails."""
    
    def __init__(self, message: str = "OpenAI API error"):
        super().__init__(service="OpenAI", message=message)


class PineconeError(ExternalServiceError):
    """Raised when Pinecone API fails."""
    
    def __init__(self, message: str = "Pinecone API error"):
        super().__init__(service="Pinecone", message=message)


class RedisError(ExternalServiceError):
    """Raised when Redis fails."""
    
    def __init__(self, message: str = "Redis error"):
        super().__init__(service="Redis", message=message)


# =============================================================================
# Exception Handler Utilities
# =============================================================================

def to_http_exception(error: TayAIError) -> HTTPException:
    """
    Convert a TayAIError to an HTTPException.
    
    Maps error codes to appropriate HTTP status codes.
    """
    status_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "ALREADY_EXISTS": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        "INACTIVE_USER": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "USAGE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    http_status = status_map.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    headers = {}
    if isinstance(error, RateLimitExceededError):
        headers["Retry-After"] = str(error.retry_after)
    
    return HTTPException(
        status_code=http_status,
        detail=error.to_dict(),
        headers=headers if headers else None
    )
