"""
Chat Schemas - Pydantic models for chat-related API operations.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# =============================================================================
# Message Models
# =============================================================================

class ChatMessage(BaseModel):
    """Chat message from database."""
    id: Optional[int] = None
    user_id: int
    message: str
    response: Optional[str] = None
    tokens_used: int = 0
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConversationMessage(BaseModel):
    """Single message in conversation history."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


# =============================================================================
# Request Models
# =============================================================================

class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_history: Optional[List[ConversationMessage]] = None
    include_sources: bool = False


class PersonaTestRequest(BaseModel):
    """Request for testing persona responses."""
    message: str = Field(..., min_length=1, max_length=4000)
    context_type: Optional[str] = Field(
        None,
        description="Force context: hair_education, business_mentorship, etc."
    )


# =============================================================================
# Response Models
# =============================================================================

class SourceInfo(BaseModel):
    """Knowledge base source information."""
    title: str
    category: Optional[str] = None
    score: float
    chunk_id: str


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str
    tokens_used: int
    message_id: Optional[int] = None
    sources: Optional[List[SourceInfo]] = None


class ChatHistoryResponse(BaseModel):
    """Response for chat history requests."""
    messages: List[ChatMessage]
    total_count: int
    has_more: bool


class PersonaTestResponse(BaseModel):
    """Response from persona testing."""
    response: str
    tokens_used: int
    context_type: str
    sources: List[Dict[str, Any]]
    system_prompt_preview: str
