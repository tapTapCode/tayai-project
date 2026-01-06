"""
Conversation Context Detection for TayAI

Handles detecting WHAT type of help the user needs based on their message.
This affects which specialized instructions TayAI uses to respond.
"""
from enum import Enum
from typing import Dict, List


class ConversationContext(str, Enum):
    """
    Types of conversation contexts that affect AI response behavior.
    
    Each context type triggers different specialized instructions
    to ensure TayAI responds appropriately.
    """
    HAIR_EDUCATION = "hair_education"
    BUSINESS_MENTORSHIP = "business_mentorship"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    TROUBLESHOOTING = "troubleshooting"
    GENERAL = "general"


# Keywords used to detect conversation context
# These are matched against user messages to determine context type
CONTEXT_KEYWORDS: Dict[ConversationContext, List[str]] = {
    ConversationContext.HAIR_EDUCATION: [
        "hair", "curl", "braid", "style", "texture", "moisture", "protein",
        "wash", "condition", "detangle", "protective", "natural", "relaxed",
        "extension", "wig", "loc", "twist", "coil", "strand", "scalp", "growth"
    ],
    ConversationContext.BUSINESS_MENTORSHIP: [
        "business", "client", "price", "pricing", "marketing", "social media",
        "instagram", "booking", "salon", "brand", "money", "income", "profit",
        "customer", "service", "charge", "start", "grow", "scale", "invest"
    ],
    ConversationContext.PRODUCT_RECOMMENDATION: [
        "product", "recommend", "buy", "purchase", "ingredient", "shampoo",
        "conditioner", "oil", "cream", "gel", "spray", "serum", "mask", "treatment"
    ],
    ConversationContext.TROUBLESHOOTING: [
        "problem", "issue", "help", "wrong", "damage", "break", "dry", "brittle",
        "falling", "thinning", "not working", "failed", "mistake", "fix", "repair"
    ],
}


def detect_conversation_context(message: str) -> ConversationContext:
    """
    Detect the conversation context from a user message using keyword matching.
    
    This analyzes the user's message to determine what type of help they need,
    which then influences how TayAI responds.
    
    Args:
        message: The user's message text
    
    Returns:
        The detected ConversationContext type
    
    Example:
        >>> detect_conversation_context("How do I price my services?")
        ConversationContext.BUSINESS_MENTORSHIP
        
        >>> detect_conversation_context("My hair is breaking")
        ConversationContext.TROUBLESHOOTING
    """
    message_lower = message.lower()
    
    # Count keyword matches for each context
    scores: Dict[ConversationContext, int] = {}
    for context, keywords in CONTEXT_KEYWORDS.items():
        scores[context] = sum(1 for kw in keywords if kw in message_lower)
    
    # Find the context with highest score
    max_score = max(scores.values())
    
    if max_score == 0:
        return ConversationContext.GENERAL
    
    # Priority order for tie-breaking (most specific first)
    priority = [
        ConversationContext.TROUBLESHOOTING,
        ConversationContext.PRODUCT_RECOMMENDATION,
        ConversationContext.BUSINESS_MENTORSHIP,
        ConversationContext.HAIR_EDUCATION,
    ]
    
    for context in priority:
        if scores.get(context, 0) == max_score:
            return context
    
    return ConversationContext.GENERAL
