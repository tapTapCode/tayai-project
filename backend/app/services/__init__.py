"""
Business Logic Services for TayAI

This module exports all service classes that contain the core business logic.
Services are responsible for:
- Interacting with the database
- Calling external APIs (OpenAI)
- Implementing business rules

Usage:
    from app.services import ChatService, RAGService, KnowledgeService
    
    # Services typically need a database session
    service = ChatService(db_session)
"""

from .base import BaseService
from .chat_service import ChatService
from .rag_service import RAGService, ChunkConfig, RetrievalResult, ContextResult
from .knowledge_service import KnowledgeService
from .usage_service import UsageService
from .user_service import UserService
from .membership_service import MembershipService, MembershipPlatform, MembershipEvent

__all__ = [
    # Base
    "BaseService",
    # Core AI services
    "ChatService",
    "RAGService",
    "KnowledgeService",
    # Supporting services
    "UsageService",
    "UserService",
    "MembershipService",
    # RAG data classes
    "ChunkConfig",
    "RetrievalResult",
    "ContextResult",
    # Membership enums
    "MembershipPlatform",
    "MembershipEvent",
]
