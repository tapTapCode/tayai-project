"""
Database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.database import Base


class UserTier(str, enum.Enum):
    """User membership tier"""
    BASIC = "basic"  # New member - 7-day trial access
    VIP = "vip"      # Elite - Full access to Community + Mentorship + Tay AI


class User(Base):
    """User model with role-based access control."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tier = Column(SQLEnum(UserTier), default=UserTier.BASIC, nullable=False)
    
    # Status flags
    is_active = Column(Boolean, default=True)
    
    # Role flags (for RBAC)
    is_admin = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    
    # Profile data from membership platform (JSON)
    profile_data = Column(JSON, nullable=True)
    
    # Trial period tracking (for Basic tier)
    trial_start_date = Column(DateTime(timezone=True), nullable=True)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatMessage(Base):
    """Chat message model"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageTracking(Base):
    """Usage tracking model"""
    __tablename__ = "usage_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    messages_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    api_cost = Column(Integer, default=0)  # Cost in micro-dollars (1/1,000,000 USD) for precision
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeBase(Base):
    """Knowledge base content model"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    extra_metadata = Column(Text, nullable=True)  # JSON string (renamed from 'metadata' - reserved)
    pinecone_id = Column(String, nullable=True, unique=True)  # Deprecated: kept for migration compatibility
    vector_id = Column(String, nullable=True, unique=True)  # New: vector embedding identifier
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VectorEmbedding(Base):
    """Vector embedding model for pgvector storage"""
    __tablename__ = "vector_embeddings"
    
    id = Column(String, primary_key=True)  # Vector ID (e.g., "kb_001_chunk_0")
    knowledge_base_id = Column(Integer, nullable=True, index=True)
    # Note: embedding column is defined as vector(1536) in database, but SQLAlchemy doesn't have native support
    # We'll handle it via raw SQL queries
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    namespace = Column(String, nullable=True, index=True)
    chunk_index = Column(Integer, nullable=True)
    parent_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MissingKBItem(Base):
    """Track missing knowledge base items detected by Tay AI"""
    __tablename__ = "missing_kb_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    question = Column(Text, nullable=False)  # Original user question
    missing_detail = Column(Text, nullable=False)  # What specific info is missing
    ai_response_preview = Column(Text, nullable=True)  # Preview of AI's response
    suggested_namespace = Column(String, nullable=True)  # Suggested KB namespace
    is_resolved = Column(Boolean, default=False, index=True)  # Whether KB item was added
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_kb_id = Column(Integer, nullable=True)  # KB item ID that resolved this
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional metadata (JSON)
    extra_metadata = Column(JSON, nullable=True)  # Store context_type, tier, etc. (renamed from 'metadata' - reserved)


class QuestionLog(Base):
    """Track all questions asked to build insights and improve content"""
    __tablename__ = "question_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    question = Column(Text, nullable=False, index=True)  # User's question
    normalized_question = Column(String, nullable=True, index=True)  # Normalized for grouping
    context_type = Column(String, nullable=True, index=True)  # Type of conversation context
    category = Column(String, nullable=True, index=True)  # Detected category
    user_tier = Column(String, nullable=True, index=True)  # User's tier at time of question
    tokens_used = Column(Integer, default=0)
    has_sources = Column(Boolean, default=False)  # Whether RAG found relevant sources
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional metadata (JSON)
    extra_metadata = Column(JSON, nullable=True)  # Store RAG scores, sources count, etc. (renamed from 'metadata' - reserved)
