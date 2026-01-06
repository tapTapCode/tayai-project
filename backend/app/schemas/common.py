"""
Common Schemas

Shared response schemas used across the application.
"""
from typing import TypeVar, Generic, Optional, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Generic Response Wrapper
# =============================================================================

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """
    Standard API response wrapper.
    
    Provides consistent response structure across all endpoints.
    """
    success: bool = True
    data: Optional[DataT] = None
    message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """
    Standard error response.
    """
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Paginated response wrapper.
    """
    success: bool = True
    data: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Common Field Types
# =============================================================================

class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class IdMixin(BaseModel):
    """Mixin for models with ID."""
    id: int
    
    class Config:
        from_attributes = True


# =============================================================================
# Status Responses
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True


class DeleteResponse(BaseModel):
    """Delete operation response."""
    message: str = "Successfully deleted"
    deleted_count: int = 1
    success: bool = True


# =============================================================================
# Pagination Parameters
# =============================================================================

class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size
