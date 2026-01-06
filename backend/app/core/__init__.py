"""
Core Module for TayAI

Central configuration, clients, and utilities used throughout the application.

This module provides:
- settings: Application configuration from environment variables
- OpenAI client: Shared, lazy-initialized API client
- Prompt engineering: Persona, context detection, prompt generation
- Rate limiting: Redis-based rate limiter
- Permissions: Role-based access control (RBAC)
- Exceptions: Custom exception classes
- Constants: Application-wide constants
- Performance: Caching and performance utilities
- Query helpers: Database query optimization utilities

Usage:
    from app.core import settings, get_openai_client
    from app.core import ConversationContext, detect_conversation_context
    from app.core import rate_limiter
    from app.core import Permission, Role, require_permission
    from app.core import NotFoundError, ValidationError
    from app.core import MAX_MESSAGE_LENGTH, DEFAULT_TEMPERATURE
"""
from app.core.config import settings
from app.core.clients import (
    get_openai_client,
    reset_clients,
)
from app.core.prompts import (
    # Persona
    PersonaConfig,
    DEFAULT_PERSONA,
    # Context
    ConversationContext,
    CONTEXT_KEYWORDS,
    detect_conversation_context,
    # Generation
    get_system_prompt,
    get_context_injection_prompt,
    # Fallbacks
    FALLBACK_RESPONSES,
)
from app.core.rate_limiter import rate_limiter, check_rate_limit_dependency
from app.core.permissions import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    TIER_FEATURES,
    has_permission,
    has_feature,
    require_permission,
    require_role,
    require_feature,
)
from app.core.exceptions import (
    TayAIError,
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
    PermissionDeniedError,
    InactiveUserError,
    RateLimitExceededError,
    UsageLimitExceededError,
    ExternalServiceError,
    OpenAIError,
    RedisError,
    to_http_exception,
)
from app.core.constants import (
    # Chat Configuration
    MAX_MESSAGE_LENGTH,
    MIN_MESSAGE_LENGTH,
    MAX_CONVERSATION_HISTORY,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_K,
    DEFAULT_SCORE_THRESHOLD,
    # Pagination
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    CHAT_HISTORY_DEFAULT_LIMIT,
    CHAT_HISTORY_MAX_LIMIT,
    # Cache TTL
    CACHE_TTL_SHORT,
    CACHE_TTL_MEDIUM,
    CACHE_TTL_LONG,
    CACHE_TTL_DAY,
    # Rate Limiting
    RATE_LIMIT_DEFAULT_PER_MINUTE,
    RATE_LIMIT_DEFAULT_PER_HOUR,
    RATE_LIMIT_TIER_MULTIPLIERS,
    # Usage Limits
    BASIC_TIER_MESSAGES_PER_MONTH,
    VIP_TIER_MESSAGES_PER_MONTH,
    TRIAL_PERIOD_DAYS,
    # Security
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    # Error Codes
    ERROR_CODES,
    MESSAGES,
)
from app.core.performance import (
    cache_result,
    cache_result_sync,
    measure_performance,
    optimize_query,
    batch_process,
    clear_cache,
)
from app.core.query_helpers import (
    QueryBuilder,
    get_paginated_results,
    count_records,
)

__all__ = [
    # Config
    "settings",
    # Clients
    "get_openai_client",
    "reset_clients",
    # Prompts
    "PersonaConfig",
    "DEFAULT_PERSONA",
    "ConversationContext",
    "CONTEXT_KEYWORDS",
    "detect_conversation_context",
    "get_system_prompt",
    "get_context_injection_prompt",
    "FALLBACK_RESPONSES",
    # Rate Limiting
    "rate_limiter",
    "check_rate_limit_dependency",
    # Permissions
    "Permission",
    "Role",
    "ROLE_PERMISSIONS",
    "TIER_FEATURES",
    "has_permission",
    "has_feature",
    "require_permission",
    "require_role",
    "require_feature",
    # Exceptions
    "TayAIError",
    "NotFoundError",
    "AlreadyExistsError",
    "ValidationError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "InvalidTokenError",
    "PermissionDeniedError",
    "InactiveUserError",
    "RateLimitExceededError",
    "UsageLimitExceededError",
    "ExternalServiceError",
    "OpenAIError",
    "RedisError",
    "to_http_exception",
    # Constants
    "MAX_MESSAGE_LENGTH",
    "MIN_MESSAGE_LENGTH",
    "MAX_CONVERSATION_HISTORY",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TOP_K",
    "DEFAULT_SCORE_THRESHOLD",
    "DEFAULT_PAGE_LIMIT",
    "MAX_PAGE_LIMIT",
    "CHAT_HISTORY_DEFAULT_LIMIT",
    "CHAT_HISTORY_MAX_LIMIT",
    "CACHE_TTL_SHORT",
    "CACHE_TTL_MEDIUM",
    "CACHE_TTL_LONG",
    "CACHE_TTL_DAY",
    "RATE_LIMIT_DEFAULT_PER_MINUTE",
    "RATE_LIMIT_DEFAULT_PER_HOUR",
    "RATE_LIMIT_TIER_MULTIPLIERS",
    "BASIC_TIER_MESSAGES_PER_MONTH",
    "VIP_TIER_MESSAGES_PER_MONTH",
    "TRIAL_PERIOD_DAYS",
    "MIN_PASSWORD_LENGTH",
    "MAX_PASSWORD_LENGTH",
    "ERROR_CODES",
    "MESSAGES",
    # Performance
    "cache_result",
    "cache_result_sync",
    "measure_performance",
    "optimize_query",
    "batch_process",
    "clear_cache",
    # Query Helpers
    "QueryBuilder",
    "get_paginated_results",
    "count_records",
]
