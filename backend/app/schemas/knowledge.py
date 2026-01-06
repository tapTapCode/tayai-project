"""
Knowledge Base Schemas - Pydantic models for knowledge base operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# Item Models
# =============================================================================

class KnowledgeBaseItem(BaseModel):
    """Knowledge base item from database."""
    id: int
    title: str
    content: str
    category: Optional[str] = None
    metadata: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# Request Models
# =============================================================================

class KnowledgeBaseCreate(BaseModel):
    """Request to create a knowledge base item."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    metadata: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    """Request to update a knowledge base item."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    metadata: Optional[str] = None
    is_active: Optional[bool] = None


class BulkUploadItem(BaseModel):
    """Single item in bulk upload."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    category: Optional[str] = Field(None, max_length=100)


class BulkUploadRequest(BaseModel):
    """Request for bulk uploading items."""
    items: List[BulkUploadItem] = Field(..., min_length=1, max_length=100)


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., min_length=1, max_length=1000)
    category: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


# =============================================================================
# Response Models
# =============================================================================

class BulkUploadResult(BaseModel):
    """Result of bulk upload operation."""
    total: int
    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = []
    created_ids: List[int] = []


class SearchResult(BaseModel):
    """Single search result."""
    id: str
    score: float
    title: Optional[str] = None
    category: Optional[str] = None
    content_preview: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from semantic search."""
    query: str
    results: List[SearchResult]
    total_results: int


class KnowledgeStats(BaseModel):
    """Statistics about the knowledge base."""
    total_items: int
    active_items: int
    categories: List[Dict[str, Any]]
    vector_count: int
    index_dimension: int


class ReindexResponse(BaseModel):
    """Response from reindex operation."""
    success_count: int
    error_count: int
    message: str
