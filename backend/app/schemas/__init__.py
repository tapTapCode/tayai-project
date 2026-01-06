"""
Pydantic Schemas for TayAI API

This module exports all request/response schemas used by the API endpoints.
Organized by domain: auth, chat, knowledge, usage, common.
"""

# Common schemas
from .common import (
    ApiResponse,
    ErrorResponse,
    PaginatedResponse,
    HealthResponse,
    MessageResponse,
    DeleteResponse,
    PaginationParams,
    TimestampMixin,
    IdMixin,
)

# Authentication schemas
from .auth import (
    Token,
    TokenData,
    TokenRefreshRequest,
    UserLogin,
    UserVerify,
    UserCreate,
    UserResponse,
    PasswordChange,
)

# Chat schemas
from .chat import (
    ChatMessage,
    ConversationMessage,
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    SourceInfo,
    PersonaTestRequest,
    PersonaTestResponse,
)

# Knowledge base schemas
from .knowledge import (
    KnowledgeBaseItem,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    BulkUploadItem,
    BulkUploadRequest,
    BulkUploadResult,
    SearchRequest,
    SearchResult,
    SearchResponse,
    KnowledgeStats,
    ReindexResponse,
)

# Usage tracking schemas
from .usage import UsageStatus

# Logging schemas
from .logging import (
    MissingKBItem,
    MissingKBItemCreate,
    MissingKBItemUpdate,
    QuestionLog,
    QuestionLogCreate,
    MissingKBStats,
    QuestionStats,
    MissingKBExport,
    QuestionExport,
    LoggingStatsResponse,
)

__all__ = [
    # Common
    "ApiResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "HealthResponse",
    "MessageResponse",
    "DeleteResponse",
    "PaginationParams",
    "TimestampMixin",
    "IdMixin",
    # Auth
    "Token",
    "TokenData",
    "TokenRefreshRequest",
    "UserLogin",
    "UserVerify",
    "UserCreate",
    "UserResponse",
    "PasswordChange",
    # Chat
    "ChatMessage",
    "ConversationMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatHistoryResponse",
    "SourceInfo",
    "PersonaTestRequest",
    "PersonaTestResponse",
    # Knowledge
    "KnowledgeBaseItem",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "BulkUploadItem",
    "BulkUploadRequest",
    "BulkUploadResult",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    "KnowledgeStats",
    "ReindexResponse",
    # Usage
    "UsageStatus",
    # Logging
    "MissingKBItem",
    "MissingKBItemCreate",
    "MissingKBItemUpdate",
    "QuestionLog",
    "QuestionLogCreate",
    "MissingKBStats",
    "QuestionStats",
    "MissingKBExport",
    "QuestionExport",
    "LoggingStatsResponse",
]
