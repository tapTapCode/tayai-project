"""
Shared API Clients - Centralized client initialization for external services.

This module provides lazy-initialized clients for:
- OpenAI (GPT-4, Embeddings)

Using centralized clients ensures:
- Single source of truth for configuration
- Efficient connection reuse
- Easier testing and mocking
"""
from typing import Optional
from openai import AsyncOpenAI

from app.core.config import settings

# Singleton instances
_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """
    Get or create the OpenAI async client.
    
    Returns:
        AsyncOpenAI client instance
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def reset_clients():
    """Reset all clients. Useful for testing."""
    global _openai_client
    _openai_client = None
