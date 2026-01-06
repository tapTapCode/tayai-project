"""
Application Constants

Centralized constants used throughout the application.
Follows DRY principle and makes configuration easier to maintain.
"""
from typing import Dict, List

# =============================================================================
# Chat Configuration
# =============================================================================

# Message limits
MAX_MESSAGE_LENGTH = 4000
MIN_MESSAGE_LENGTH = 1
MAX_CONVERSATION_HISTORY = 10

# OpenAI API defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.7

# RAG Configuration
RAG_TOP_K = 5
RAG_SCORE_THRESHOLD = 0.7
RAG_CHUNK_SIZE = 500
RAG_CHUNK_OVERLAP = 50

# =============================================================================
# Pagination Defaults
# =============================================================================

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500
DEFAULT_PAGE_OFFSET = 0

# Chat history pagination
CHAT_HISTORY_DEFAULT_LIMIT = 50
CHAT_HISTORY_MAX_LIMIT = 200

# =============================================================================
# Cache TTL (Time To Live in seconds)
# =============================================================================

CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 1800  # 30 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_DAY = 86400  # 24 hours

# Usage cache TTL
USAGE_CACHE_TTL = 3600  # 1 hour

# =============================================================================
# Rate Limiting Defaults
# =============================================================================

RATE_LIMIT_DEFAULT_PER_MINUTE = 60
RATE_LIMIT_DEFAULT_PER_HOUR = 1000

# Tier multipliers for rate limits
RATE_LIMIT_TIER_MULTIPLIERS: Dict[str, int] = {
    "basic": 1,
    "vip": 5,
}

# =============================================================================
# Usage Limits
# =============================================================================

# Message limits per tier (per month)
BASIC_TIER_MESSAGES_PER_MONTH = 50
VIP_TIER_MESSAGES_PER_MONTH = 1000

# Trial period
TRIAL_PERIOD_DAYS = 7

# =============================================================================
# API Response Messages
# =============================================================================

MESSAGES = {
    "SUCCESS": "Operation completed successfully",
    "NOT_FOUND": "Resource not found",
    "UNAUTHORIZED": "Authentication required",
    "FORBIDDEN": "Insufficient permissions",
    "VALIDATION_ERROR": "Request validation failed",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded. Please try again later.",
    "USAGE_LIMIT_EXCEEDED": "Usage limit exceeded",
    "INTERNAL_ERROR": "An unexpected error occurred",
}

# =============================================================================
# HTTP Headers
# =============================================================================

HEADERS = {
    "RATE_LIMIT_LIMIT": "X-RateLimit-Limit",
    "RATE_LIMIT_REMAINING": "X-RateLimit-Remaining",
    "RETRY_AFTER": "Retry-After",
}

# =============================================================================
# Database Query Limits
# =============================================================================

MAX_QUERY_RESULTS = 1000
BATCH_SIZE = 100

# =============================================================================
# Security Constants
# =============================================================================

# Password requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Token expiration (in minutes/days)
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# =============================================================================
# File/Content Limits
# =============================================================================

MAX_CONTENT_LENGTH = 100000  # 100KB for knowledge base content
MAX_TITLE_LENGTH = 200

# =============================================================================
# Error Codes
# =============================================================================

ERROR_CODES = {
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "AUTHENTICATION_ERROR": "AUTHENTICATION_ERROR",
    "AUTHORIZATION_ERROR": "AUTHORIZATION_ERROR",
    "NOT_FOUND": "NOT_FOUND",
    "ALREADY_EXISTS": "ALREADY_EXISTS",
    "RATE_LIMIT_EXCEEDED": "RATE_LIMIT_EXCEEDED",
    "USAGE_LIMIT_EXCEEDED": "USAGE_LIMIT_EXCEEDED",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}

# =============================================================================
# Allowed Origins (for CORS)
# =============================================================================

DEFAULT_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
]

# =============================================================================
# Excluded Paths from Rate Limiting
# =============================================================================

RATE_LIMIT_EXCLUDED_PATHS: List[str] = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]
