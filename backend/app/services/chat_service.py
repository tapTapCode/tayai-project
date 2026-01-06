"""
Chat Service - Business logic for chat operations with RAG

Handles:
1. Processing user messages with RAG-enhanced context
2. Managing conversation history
3. Interacting with OpenAI API
4. Storing chat messages
5. Streaming responses via SSE
"""
import logging
import json
from typing import List, Dict, Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from app.core.config import settings
from app.core.clients import get_openai_client
from app.core.performance import cache_result, measure_performance, optimize_query
from app.core.constants import (
    MAX_CONVERSATION_HISTORY,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_K,
    DEFAULT_SCORE_THRESHOLD,
    CHAT_HISTORY_DEFAULT_LIMIT,
)
from app.core.prompts import (
    get_system_prompt,
    get_context_injection_prompt,
    detect_conversation_context,
    ConversationContext,
    FALLBACK_RESPONSES
)
from app.db.models import ChatMessage, MissingKBItem, QuestionLog
from app.services.rag_service import RAGService, ContextResult
from app.schemas.chat import ChatResponse
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat-related operations."""
    
    # Configuration (using constants)
    MAX_HISTORY = MAX_CONVERSATION_HISTORY
    TEMPERATURE = DEFAULT_TEMPERATURE
    MAX_TOKENS = DEFAULT_MAX_TOKENS
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_service = RAGService(db=db)
    
    # -------------------------------------------------------------------------
    # Message Processing
    # -------------------------------------------------------------------------
    
    @measure_performance
    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        include_sources: bool = False,
        user_tier: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat message using RAG and return AI response.
        
        Args:
            user_id: The user's ID
            message: The user's message
            conversation_history: Previous messages in conversation
            include_sources: Whether to include source info
        
        Returns:
            ChatResponse with AI response and metadata
        """
        try:
            # Detect context type
            context_type = detect_conversation_context(message)
            logger.info(f"Context: {context_type.value} for: {message[:50]}...")
            
            # Retrieve RAG context
            context_result = await self.rag_service.retrieve_context(
                query=message,
                top_k=DEFAULT_TOP_K,
                score_threshold=DEFAULT_SCORE_THRESHOLD,
                include_sources=True
            )
            
            # Extract context string
            context = (
                context_result.context 
                if isinstance(context_result, ContextResult) 
                else context_result
            )
            
            # Build messages and call API
            messages = self._build_messages(
                message, context, conversation_history, context_type, user_tier
            )
            
            response = await get_openai_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS
            )
            
            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Save to database
            chat_message = ChatMessage(
                user_id=user_id,
                message=message,
                response=ai_response,
                tokens_used=tokens_used
            )
            self.db.add(chat_message)
            await self.db.commit()
            await self.db.refresh(chat_message)
            
            logger.info(f"Processed message for user {user_id}, tokens: {tokens_used}")
            
            # Log question and check for missing KB items (async logging)
            await self._log_question_and_missing_kb(
                user_id=user_id,
                question=message,
                ai_response=ai_response,
                context_type=context_type,
                context_result=context_result,
                user_tier=user_tier,
                tokens_used=tokens_used
            )
            
            # Build response
            result = ChatResponse(
                response=ai_response,
                tokens_used=tokens_used,
                message_id=chat_message.id
            )
            
            if include_sources and isinstance(context_result, ContextResult):
                result.sources = context_result.sources
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ChatResponse(
                response=FALLBACK_RESPONSES["error_graceful"],
                tokens_used=0,
                message_id=None
            )
    
    def _build_messages(
        self,
        user_message: str,
        context: str,
        history: Optional[List[Dict]],
        context_type: ConversationContext,
        user_tier: Optional[str] = None
    ) -> List[Dict]:
        """Build the message array for OpenAI API."""
        messages = [
            {"role": "system", "content": get_system_prompt(
                context_type=context_type,
                user_tier=user_tier
            )}
        ]
        
        # Add RAG context
        if context:
            messages.append({
                "role": "system",
                "content": get_context_injection_prompt(context, user_message)
            })
        
        # Add conversation history
        if history:
            for msg in history[-self.MAX_HISTORY:]:
                if self._is_valid_message(msg):
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    @staticmethod
    def _is_valid_message(msg: Dict) -> bool:
        """Validate a message dictionary."""
        return (
            isinstance(msg, dict)
            and msg.get("role") in ("user", "assistant", "system")
            and "content" in msg
        )
    
    # -------------------------------------------------------------------------
    # Chat History
    # -------------------------------------------------------------------------
    
    @measure_performance
    async def get_chat_history(
        self,
        user_id: int,
        limit: int = CHAT_HISTORY_DEFAULT_LIMIT,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get chat history for a user."""
        # Optimize query with proper indexing and limits
        query = select(ChatMessage).where(ChatMessage.user_id == user_id)
        query = query.order_by(desc(ChatMessage.created_at))
        query = optimize_query(query, limit=limit, offset=offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    @measure_performance
    async def get_conversation_context(
        self,
        user_id: int,
        message_count: int = 5
    ) -> List[Dict]:
        """Get recent conversation as context for new messages."""
        # Use optimized query with limit
        messages = await self.get_chat_history(user_id, limit=message_count)
        
        # Convert to conversation format (chronological order)
        context = []
        for msg in reversed(messages):
            context.append({"role": "user", "content": msg.message})
            if msg.response:
                context.append({"role": "assistant", "content": msg.response})
        
        return context
    
    async def clear_chat_history(self, user_id: int) -> int:
        """Clear all chat history for a user."""
        # Use bulk delete for better performance
        result = await self.db.execute(
            delete(ChatMessage).where(ChatMessage.user_id == user_id)
        )
        count = result.rowcount or 0
        
        await self.db.commit()
        logger.info(f"Cleared {count} messages for user {user_id}")
        
        return count
    
    # -------------------------------------------------------------------------
    # Persona Testing
    # -------------------------------------------------------------------------
    
    async def test_persona_response(
        self,
        test_message: str,
        context_type: Optional[ConversationContext] = None,
        user_tier: Optional[str] = None
    ) -> Dict:
        """
        Test AI response without saving to database.
        
        Args:
            test_message: The test message
            context_type: Optional forced context type
        
        Returns:
            Dictionary with response and metadata
        """
        # Detect context if not provided
        if context_type is None:
            context_type = detect_conversation_context(test_message)
        
        # Get RAG context
        context_result = await self.rag_service.retrieve_context(
            query=test_message,
            top_k=DEFAULT_TOP_K,
            include_sources=True
        )
        
        context = (
            context_result.context 
            if isinstance(context_result, ContextResult) 
            else context_result
        )
        
        # Build messages and call API
        messages = self._build_messages(test_message, context, None, context_type, user_tier)
        
        response = await get_openai_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS
        )
        
        sources = (
            context_result.sources 
            if isinstance(context_result, ContextResult) 
            else []
        )
        
        return {
            "response": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "context_type": context_type.value,
            "sources": sources,
            "system_prompt_preview": messages[0]["content"][:500] + "..."
        }
    
    # -------------------------------------------------------------------------
    # Streaming Responses (SSE)
    # -------------------------------------------------------------------------
    
    async def process_message_stream(
        self,
        user_id: int,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        include_sources: bool = False,
        user_tier: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a chat message and stream the response via SSE.
        
        Yields SSE-formatted events:
        - 'start': Initial event with context info
        - 'chunk': Text chunks as they arrive
        - 'sources': Source information (if requested)
        - 'done': Final event with message ID and token count
        - 'error': Error event if something goes wrong
        
        Args:
            user_id: The user's ID
            message: The user's message
            conversation_history: Previous messages in conversation
            include_sources: Whether to include source info
            
        Yields:
            SSE-formatted event strings
        """
        try:
            # Detect context type
            context_type = detect_conversation_context(message)
            logger.info(f"[Stream] Context: {context_type.value} for: {message[:50]}...")
            
            # Send start event
            yield self._format_sse_event("start", {
                "context_type": context_type.value,
                "message": "Processing your message..."
            })
            
            # Retrieve RAG context
            context_result = await self.rag_service.retrieve_context(
                query=message,
                top_k=DEFAULT_TOP_K,
                score_threshold=DEFAULT_SCORE_THRESHOLD,
                include_sources=True
            )
            
            # Extract context string
            context = (
                context_result.context 
                if isinstance(context_result, ContextResult) 
                else context_result
            )
            
            # Build messages
            messages = self._build_messages(
                message, context, conversation_history, context_type, user_tier
            )
            
            # Call OpenAI with streaming
            stream = await get_openai_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
                stream=True
            )
            
            # Collect full response for saving
            full_response = ""
            
            # Stream chunks
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield self._format_sse_event("chunk", {"content": content})
            
            # Estimate tokens (actual count not available in streaming)
            estimated_tokens = len(full_response.split()) * 1.3  # Rough estimate
            
            # Save to database
            chat_message = ChatMessage(
                user_id=user_id,
                message=message,
                response=full_response,
                tokens_used=int(estimated_tokens)
            )
            self.db.add(chat_message)
            await self.db.commit()
            await self.db.refresh(chat_message)
            
            # Log question and check for missing KB items (async logging)
            await self._log_question_and_missing_kb(
                user_id=user_id,
                question=message,
                ai_response=full_response,
                context_type=context_type,
                context_result=context_result,
                user_tier=user_tier,
                tokens_used=int(estimated_tokens)
            )
            
            # Send sources if requested
            if include_sources and isinstance(context_result, ContextResult):
                sources_data = [
                    {
                        "title": s.title,
                        "category": s.category,
                        "score": s.score,
                        "chunk_id": s.chunk_id
                    }
                    for s in context_result.sources
                ]
                yield self._format_sse_event("sources", {"sources": sources_data})
            
            # Send done event
            yield self._format_sse_event("done", {
                "message_id": chat_message.id,
                "tokens_used": int(estimated_tokens)
            })
            
            logger.info(f"[Stream] Completed for user {user_id}, tokens: {estimated_tokens}")
            
        except Exception as e:
            logger.error(f"[Stream] Error: {e}")
            yield self._format_sse_event("error", {
                "message": FALLBACK_RESPONSES["error_graceful"]
            })
    
    @staticmethod
    def _format_sse_event(event_type: str, data: dict) -> str:
        """
        Format data as an SSE event.
        
        Args:
            event_type: The event name (start, chunk, done, error)
            data: The event data
            
        Returns:
            SSE-formatted string
        """
        json_data = json.dumps(data)
        return f"event: {event_type}\ndata: {json_data}\n\n"
    
    # -------------------------------------------------------------------------
    # Logging & Analytics
    # -------------------------------------------------------------------------
    
    async def _log_question_and_missing_kb(
        self,
        user_id: int,
        question: str,
        ai_response: str,
        context_type: ConversationContext,
        context_result: ContextResult,
        user_tier: Optional[str] = None,
        tokens_used: int = 0
    ) -> None:
        """
        Log the question and detect/log missing KB items.
        
        This creates the knowledge feedback loop:
        User → Tay AI detects missing info → logs it → Annika uploads → PostgreSQL pgvector updates → Tay AI gets smarter
        """
        try:
            # Always log the question
            normalized_question = self._normalize_question(question)
            has_sources = isinstance(context_result, ContextResult) and len(context_result.sources) > 0
            
            # Determine category from context
            category = self._determine_category(question, context_type)
            
            question_log = QuestionLog(
                user_id=user_id,
                question=question,
                normalized_question=normalized_question,
                context_type=context_type.value,
                category=category,
                user_tier=user_tier,
                tokens_used=tokens_used,
                has_sources=has_sources,
                extra_metadata={
                    "rag_score_avg": (
                        sum(s.score for s in context_result.sources) / len(context_result.sources)
                        if has_sources else None
                    ),
                    "sources_count": len(context_result.sources) if has_sources else 0
                }
            )
            self.db.add(question_log)
            
            # Check if AI response indicates missing knowledge
            missing_kb_data = self._detect_missing_kb(question, ai_response, context_result)
            
            if missing_kb_data:
                missing_kb_item = MissingKBItem(
                    user_id=user_id,
                    question=question,
                    missing_detail=missing_kb_data["missing_detail"],
                    ai_response_preview=ai_response[:500],  # First 500 chars
                    suggested_namespace=missing_kb_data.get("suggested_namespace"),
                    extra_metadata={
                        "context_type": context_type.value,
                        "user_tier": user_tier,
                        "rag_score": missing_kb_data.get("rag_score"),
                        "has_sources": has_sources
                    }
                )
                self.db.add(missing_kb_item)
                logger.info(f"Missing KB item logged: {missing_kb_data['missing_detail'][:100]}")
            
            # Commit both logs
            await self.db.commit()
            
        except Exception as e:
            # Don't fail the request if logging fails
            logger.error(f"Error logging question/missing KB: {e}")
    
    @staticmethod
    def _detect_missing_kb(question: str, ai_response: str, context_result: ContextResult) -> Optional[Dict]:
        """
        Detect if the AI response indicates missing knowledge.
        
        Looks for phrases like:
        - "isn't in my brain yet"
        - "don't have that info"
        - "not in my brain"
        - "I don't have"
        - Low RAG scores
        
        Returns dict with missing_detail and suggested_namespace if detected, None otherwise.
        """
        # Check for missing KB indicators in response
        missing_indicators = [
            r"isn't in my brain",
            r"not in my brain",
            r"don't have that",
            r"don't have this",
            r"don't have the",
            r"can't find",
            r"don't have access to",
            r"isn't available",
            r"not available in",
        ]
        
        response_lower = ai_response.lower()
        has_missing_indicator = any(re.search(pattern, response_lower) for pattern in missing_indicators)
        
        # Check RAG context quality
        has_good_sources = isinstance(context_result, ContextResult) and (
            len(context_result.sources) == 0 or
            any(s.score < 0.7 for s in context_result.sources)  # Low confidence scores
        )
        
        if has_missing_indicator or has_good_sources:
            # Extract missing detail from question and response
            missing_detail = question  # Start with the question
            
            # Try to extract more specific detail from response
            # Look for phrases after "isn't in my brain" or similar
            detail_patterns = [
                r"isn't in my brain[^.]*\.\s*([^.]*)",
                r"don't have that[^.]*\.\s*([^.]*)",
                r"don't have the ([^.]*)",
            ]
            
            for pattern in detail_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    missing_detail = f"{question} - Specifically: {match.group(1)}"
                    break
            
            # Suggest namespace based on question content
            suggested_namespace = ChatService._suggest_namespace(question)
            
            return {
                "missing_detail": missing_detail.strip(),
                "suggested_namespace": suggested_namespace,
                "rag_score": (
                    min(s.score for s in context_result.sources) if 
                    isinstance(context_result, ContextResult) and context_result.sources else None
                )
            }
        
        return None
    
    @staticmethod
    def _suggest_namespace(question: str) -> Optional[str]:
        """Suggest a KB namespace based on question content."""
        question_lower = question.lower()
        
        # Namespace keywords mapping
        namespace_keywords = {
            "techniques": ["install", "lace", "melting", "plucking", "tinting", "bleaching", "wig construction", "bald cap"],
            "vendor": ["vendor", "supplier", "hair", "quality", "sample", "moq", "shipping", "pricing", "bundle"],
            "business": ["price", "pricing", "profit", "margin", "shopify", "brand", "niche", "packaging", "refund"],
            "content": ["hook", "reel", "script", "story", "content", "caption", "post", "social media"],
            "mindset": ["confidence", "imposter", "perfection", "block", "motivation", "fear", "consistency"],
            "offers": ["tutorial", "mentorship", "course", "community", "masterclass", "trip", "offer"]
        }
        
        for namespace, keywords in namespace_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return namespace
        
        return "faqs"  # Default to FAQs
    
    @staticmethod
    def _normalize_question(question: str) -> str:
        """
        Normalize a question for grouping similar questions.
        
        This helps identify top asked questions even with slight variations.
        """
        # Convert to lowercase
        normalized = question.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common question prefixes
        prefixes = ["how do i", "how can i", "what is", "what are", "when should", "where can"]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
        
        # Remove trailing question marks and punctuation
        normalized = normalized.rstrip('?.,!')
        
        return normalized
    
    @staticmethod
    def _determine_category(question: str, context_type: ConversationContext) -> Optional[str]:
        """Determine question category based on content and context."""
        question_lower = question.lower()
        
        # Map context types to categories
        context_category_map = {
            ConversationContext.HAIR_EDUCATION: "techniques",
            ConversationContext.BUSINESS_MENTORSHIP: "business",
            ConversationContext.PRODUCT_RECOMMENDATION: "vendor",
            ConversationContext.TROUBLESHOOTING: "techniques",
            ConversationContext.GENERAL: None
        }
        
        category = context_category_map.get(context_type)
        
        # Override with specific keywords if found
        if "vendor" in question_lower or "supplier" in question_lower:
            category = "vendor"
        elif "price" in question_lower or "cost" in question_lower:
            category = "business"
        elif "content" in question_lower or "reel" in question_lower:
            category = "content"
        
        return category
