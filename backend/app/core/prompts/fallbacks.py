"""
Fallback Responses for TayAI

Pre-defined responses for edge cases where normal processing isn't possible.
These maintain the mentor voice even in error situations.
"""

FALLBACK_RESPONSES = {
    # When user asks about something outside TayAI's expertise
    "unknown_topic": (
        "I appreciate you asking! That's a bit outside my wheelhouse - I'm really "
        "focused on hair and building beauty businesses. But if there's anything "
        "hair-related or business-related I can help you with, I'm here for it!"
    ),
    
    # When more information is needed to give good advice
    "need_more_info": (
        "I want to give you advice that actually helps YOUR situation. Can you "
        "tell me a bit more? Like what's your hair type/porosity, or what stage "
        "your business is at? The more I know, the better I can help you."
    ),
    
    # When an error occurs - maintains friendly tone
    "error_graceful": (
        "Okay, something went sideways on my end! Can you try asking that again? "
        "I want to make sure I give you a solid answer."
    ),
}
