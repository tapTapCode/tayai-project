"""
Logging Schemas - Pydantic models for missing KB items and question tracking.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# Missing KB Item Models
# =============================================================================

class MissingKBItemBase(BaseModel):
    """Base model for missing KB item."""
    question: str = Field(..., description="Original user question")
    missing_detail: str = Field(..., description="What specific information is missing")
    suggested_namespace: Optional[str] = Field(None, description="Suggested KB namespace")


class MissingKBItemCreate(MissingKBItemBase):
    """Request to create a missing KB item log."""
    user_id: int
    ai_response_preview: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="extra_metadata")
    
    class Config:
        populate_by_name = True  # Allow both 'metadata' and 'extra_metadata' in input


class MissingKBItemUpdate(BaseModel):
    """Request to update a missing KB item (e.g., mark as resolved)."""
    is_resolved: Optional[bool] = None
    resolved_by_kb_id: Optional[int] = None


class MissingKBItem(MissingKBItemBase):
    """Missing KB item from database."""
    id: int
    user_id: int
    ai_response_preview: Optional[str] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by_kb_id: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = Field(None, alias="extra_metadata")
    
    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both 'metadata' and 'extra_metadata' in input


# =============================================================================
# Question Log Models
# =============================================================================

class QuestionLogBase(BaseModel):
    """Base model for question log."""
    question: str = Field(..., description="User's question")
    context_type: Optional[str] = None
    category: Optional[str] = None
    normalized_question: Optional[str] = None


class QuestionLogCreate(QuestionLogBase):
    """Request to create a question log entry."""
    user_id: int
    user_tier: Optional[str] = None
    tokens_used: int = 0
    has_sources: bool = False
    metadata: Optional[Dict[str, Any]] = Field(None, alias="extra_metadata")
    
    class Config:
        populate_by_name = True  # Allow both 'metadata' and 'extra_metadata' in input


class QuestionLog(QuestionLogBase):
    """Question log entry from database."""
    id: int
    user_id: int
    user_tier: Optional[str] = None
    tokens_used: int
    has_sources: bool
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = Field(None, alias="extra_metadata")
    
    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both 'metadata' and 'extra_metadata' in input


# =============================================================================
# Statistics & Aggregations
# =============================================================================

class MissingKBStats(BaseModel):
    """Statistics about missing KB items."""
    total_unresolved: int
    total_resolved: int
    by_namespace: Dict[str, int]
    recent_items: List[MissingKBItem]


class QuestionStats(BaseModel):
    """Statistics about questions."""
    total_questions: int
    top_questions: List[Dict[str, Any]]  # [{question, count, first_asked, last_asked}]
    by_category: Dict[str, int]
    by_context_type: Dict[str, int]
    recent_questions: List[QuestionLog]


# =============================================================================
# Export Models (for Notion/Sheets/Airtable)
# =============================================================================

class MissingKBExport(BaseModel):
    """Export format for missing KB items."""
    id: int
    question: str
    missing_detail: str
    suggested_namespace: Optional[str]
    user_id: int
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None


class QuestionExport(BaseModel):
    """Export format for questions."""
    id: int
    question: str
    normalized_question: Optional[str]
    category: Optional[str]
    context_type: Optional[str]
    user_id: int
    user_tier: Optional[str]
    count: int = 1  # For aggregated exports
    first_asked: datetime
    last_asked: datetime


# =============================================================================
# Response Models
# =============================================================================

class LoggingStatsResponse(BaseModel):
    """Complete logging statistics response."""
    missing_kb: MissingKBStats
    questions: QuestionStats

