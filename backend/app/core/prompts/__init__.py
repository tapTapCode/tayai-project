"""
Prompt Engineering System for TayAI

This package provides the complete prompt engineering system:
- Persona: WHO TayAI is (identity, expertise, style)
- Context: WHAT type of help is needed (hair, business, etc.)
- Generation: HOW prompts are built for the OpenAI API
- Fallbacks: Graceful handling of edge cases

Usage:
    from app.core.prompts import (
        PersonaConfig,
        DEFAULT_PERSONA,
        ConversationContext,
        detect_conversation_context,
        get_system_prompt,
        get_context_injection_prompt,
        FALLBACK_RESPONSES
    )
"""
from .persona import PersonaConfig, DEFAULT_PERSONA
from .context import ConversationContext, CONTEXT_KEYWORDS, detect_conversation_context
from .generation import get_system_prompt, get_context_injection_prompt
from .fallbacks import FALLBACK_RESPONSES

__all__ = [
    # Persona
    "PersonaConfig",
    "DEFAULT_PERSONA",
    # Context
    "ConversationContext",
    "CONTEXT_KEYWORDS",
    "detect_conversation_context",
    # Generation
    "get_system_prompt",
    "get_context_injection_prompt",
    # Fallbacks
    "FALLBACK_RESPONSES",
]
