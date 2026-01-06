"""
Chat Endpoints - API operations for chat functionality.

Provides:
- Standard chat endpoint with JSON response
- Streaming chat endpoint with Server-Sent Events (SSE)
- WebSocket endpoint for real-time bidirectional chat
- Chat history management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
import logging

from app.db.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessage
)
from app.services.chat_service import ChatService
from app.services.usage_service import UsageService
from app.core.exceptions import UsageLimitExceededError, to_http_exception
from app.core.constants import CHAT_HISTORY_DEFAULT_LIMIT, CHAT_HISTORY_MAX_LIMIT
from app.api.v1.decorators import handle_service_errors, validate_input
from app.dependencies import get_current_user
from app.utils.text import sanitize_user_input, validate_message_content

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
@handle_service_errors
@validate_input
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a chat message and get AI response.
    
    The message is processed through the RAG pipeline with context
    from the knowledge base.
    """
    # Validate and sanitize input
    is_valid, error_msg = validate_message_content(request.message)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    sanitized_message = sanitize_user_input(request.message)
    
    # Check usage limits (raises UsageLimitExceededError if exceeded)
    usage_service = UsageService(db)
    try:
        await usage_service.check_usage_limit(
            current_user["user_id"], 
            current_user["tier"]
        )
    except UsageLimitExceededError as e:
        http_exc = to_http_exception(e)
        raise HTTPException(
            status_code=http_exc.status_code,
            detail=e.to_dict()
        )
    
    # Convert conversation history
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
    
    # Process message
    chat_service = ChatService(db)
    response = await chat_service.process_message(
        user_id=current_user["user_id"],
        message=sanitized_message,
        conversation_history=history,
        include_sources=request.include_sources,
        user_tier=current_user["tier"]
    )
    
    # Track usage
    await usage_service.record_usage(
        user_id=current_user["user_id"],
        tokens_used=response.tokens_used
    )
    
    return response


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a chat message and get streaming AI response via Server-Sent Events.
    
    Returns a stream of SSE events:
    - `start`: Initial event with context type
    - `chunk`: Text chunks as they arrive from the AI
    - `sources`: Knowledge base sources used (if requested)
    - `done`: Final event with message ID and token count
    - `error`: Error event if something goes wrong
    
    Example client usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/chat/stream?...');
    eventSource.addEventListener('chunk', (e) => {
        const data = JSON.parse(e.data);
        appendToResponse(data.content);
    });
    ```
    """
    # Check usage limits (raises UsageLimitExceededError if exceeded)
    usage_service = UsageService(db)
    try:
        await usage_service.check_usage_limit(
            current_user["user_id"], 
            current_user["tier"]
        )
    except UsageLimitExceededError as e:
        http_exc = to_http_exception(e)
        raise HTTPException(
            status_code=http_exc.status_code,
            detail=e.to_dict()
        )
    
    # Convert conversation history
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
    
    # Create streaming response
    chat_service = ChatService(db)
    
    async def generate():
        """Generate SSE events from the chat stream."""
        async for event in chat_service.process_message_stream(
            user_id=current_user["user_id"],
            message=request.message,
            conversation_history=history,
            include_sources=request.include_sources,
            user_tier=current_user["tier"]
        ):
            yield event
        
        # Record usage after streaming completes
        # Note: Actual token count tracked in the service
        await usage_service.record_usage(
            user_id=current_user["user_id"],
            tokens_used=0  # Will be updated from stored message
        )
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/history", response_model=ChatHistoryResponse)
@handle_service_errors
async def get_chat_history(
    limit: int = Query(CHAT_HISTORY_DEFAULT_LIMIT, ge=1, le=CHAT_HISTORY_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get chat history for the current user."""
    chat_service = ChatService(db)
    
    # Get one extra to check for more
    messages = await chat_service.get_chat_history(
        user_id=current_user["user_id"],
        limit=limit + 1,
        offset=offset
    )
    
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]
    
    return ChatHistoryResponse(
        messages=messages,
        total_count=len(messages),
        has_more=has_more
    )


@router.get("/context")
async def get_conversation_context(
    message_count: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get recent conversation for continuing a chat."""
    chat_service = ChatService(db)
    context = await chat_service.get_conversation_context(
        user_id=current_user["user_id"],
        message_count=message_count
    )
    return {"conversation_history": context}


@router.delete("/history")
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Clear all chat history for the current user."""
    chat_service = ChatService(db)
    deleted = await chat_service.clear_chat_history(current_user["user_id"])
    return {"message": f"Deleted {deleted} messages", "deleted_count": deleted}


# =============================================================================
# WebSocket Endpoint for Real-Time Chat
# =============================================================================

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional chat.
    
    Supports:
    - Real-time message sending/receiving
    - Streaming AI responses
    - Connection management
    
    Message Format (Client → Server):
    ```json
    {
        "type": "message",
        "content": "user message text",
        "token": "jwt_access_token",
        "conversation_history": [...]
    }
    ```
    
    Message Format (Server → Client):
    ```json
    {
        "type": "start" | "chunk" | "sources" | "done" | "error",
        "data": {...}
    }
    ```
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    user_id = None
    user_tier = None
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                # Extract token and verify user
                token = data.get("token")
                if not token:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Authentication required"}
                    })
                    continue
                
                # Verify token and get user
                from app.core.security import decode_access_token
                from app.db.database import get_db
                
                payload = decode_access_token(token)
                if not payload:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid or expired token"}
                    })
                    continue
                
                user_id = payload.get("user_id")
                user_tier = payload.get("tier", "basic")
                
                # Get database session
                from app.db.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    # Initialize services
                    chat_service = ChatService(db)
                    usage_service = UsageService(db)
                    
                    # Check usage limits
                    try:
                        await usage_service.check_usage_limit(user_id, user_tier)
                    except UsageLimitExceededError as e:
                        await websocket.send_json({
                            "type": "error",
                            "data": e.to_dict()
                        })
                        continue
                    
                    # Get message content
                    message_content = data.get("content", "")
                    conversation_history = data.get("conversation_history", [])
                    include_sources = data.get("include_sources", False)
                    
                    if not message_content:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Message content is required"}
                        })
                        continue
                    
                    # Send start event
                    await websocket.send_json({
                        "type": "start",
                        "data": {
                            "message": "Processing your message...",
                            "context_type": "processing"
                        }
                    })
                    
                    # Process message with streaming
                    full_response = ""
                    sources = []
                    
                    async for event in chat_service.process_message_stream(
                        user_id=user_id,
                        message=message_content,
                        conversation_history=conversation_history,
                        include_sources=include_sources,
                        user_tier=user_tier
                    ):
                        # Parse SSE event and send as WebSocket message
                        if event.startswith("event: "):
                            lines = event.strip().split("\n")
                            event_type = None
                            event_data = None
                            
                            for line in lines:
                                if line.startswith("event: "):
                                    event_type = line[7:]
                                elif line.startswith("data: "):
                                    event_data = json.loads(line[6:])
                            
                            if event_type and event_data:
                                # Send chunk events in real-time
                                if event_type == "chunk":
                                    full_response += event_data.get("content", "")
                                    await websocket.send_json({
                                        "type": "chunk",
                                        "data": event_data
                                    })
                                elif event_type == "sources":
                                    sources = event_data.get("sources", [])
                                    await websocket.send_json({
                                        "type": "sources",
                                        "data": event_data
                                    })
                                elif event_type == "done":
                                    # Record usage
                                    await usage_service.record_usage(
                                        user_id=user_id,
                                        tokens_used=event_data.get("tokens_used", 0)
                                    )
                                    await websocket.send_json({
                                        "type": "done",
                                        "data": event_data
                                    })
                                elif event_type == "error":
                                    await websocket.send_json({
                                        "type": "error",
                                        "data": event_data
                                    })
                
            elif message_type == "ping":
                # Heartbeat/ping
                await websocket.send_json({"type": "pong"})
            
            elif message_type == "close":
                # Client-initiated close
                break
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": "An error occurred processing your message"}
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
