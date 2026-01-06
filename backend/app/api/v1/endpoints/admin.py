"""
Admin Endpoints - Administrative operations for TayAI.

Provides:
- Knowledge base CRUD operations
- Bulk upload functionality
- Persona testing
- System statistics
- User management and activity monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import User, ChatMessage, UsageTracking, UserTier, MissingKBItem, QuestionLog
from app.schemas.knowledge import (
    KnowledgeBaseItem,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    BulkUploadRequest,
    BulkUploadResult,
    KnowledgeStats,
    SearchRequest,
    SearchResponse,
    SearchResult,
    ReindexResponse
)
from app.schemas.logging import (
    MissingKBItem as MissingKBItemSchema,
    MissingKBItemUpdate,
    QuestionLog as QuestionLogSchema,
    MissingKBStats,
    QuestionStats,
    MissingKBExport,
    QuestionExport,
    LoggingStatsResponse,
)
from app.schemas.chat import PersonaTestRequest, PersonaTestResponse
from app.schemas.auth import UserResponse
from app.services.knowledge_service import KnowledgeService
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.services.usage_service import UsageService
from app.core import ConversationContext
from app.utils import truncate_text
from app.dependencies import get_current_admin

router = APIRouter()


# =============================================================================
# Knowledge Base CRUD
# =============================================================================

@router.post("/knowledge", response_model=KnowledgeBaseItem)
async def create_knowledge_item(
    item: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Create a new knowledge base item."""
    service = KnowledgeService(db)
    return await service.create_knowledge_item(item)


@router.get("/knowledge", response_model=List[KnowledgeBaseItem])
async def list_knowledge_items(
    category: Optional[str] = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """List knowledge base items with optional filtering."""
    from app.core.performance import optimize_query
    service = KnowledgeService(db)
    # Optimize limit to prevent excessive queries
    optimized_limit = min(limit, 500)  # Cap at 500
    return await service.list_knowledge_items(
        category=category,
        active_only=active_only,
        limit=optimized_limit,
        offset=offset
    )


@router.get("/knowledge/{item_id}", response_model=KnowledgeBaseItem)
async def get_knowledge_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get a single knowledge base item."""
    service = KnowledgeService(db)
    item = await service.get_knowledge_item(item_id)
    
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.put("/knowledge/{item_id}", response_model=KnowledgeBaseItem)
async def update_knowledge_item(
    item_id: int,
    update: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Update an existing knowledge base item."""
    service = KnowledgeService(db)
    item = await service.update_knowledge_item(item_id, update)
    
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.delete("/knowledge/{item_id}")
async def delete_knowledge_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Delete a knowledge base item."""
    service = KnowledgeService(db)
    deleted = await service.delete_knowledge_item(item_id)
    
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return {"message": "Item deleted successfully"}


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/knowledge/bulk", response_model=BulkUploadResult)
async def bulk_upload(
    request: BulkUploadRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Bulk upload multiple knowledge base items."""
    service = KnowledgeService(db)
    
    items = [
        KnowledgeBaseCreate(
            title=item.title,
            content=item.content,
            category=item.category
        )
        for item in request.items
    ]
    
    return await service.bulk_create(items)


@router.post("/knowledge/reindex", response_model=ReindexResponse)
async def reindex_knowledge(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Reindex all knowledge base items in PostgreSQL pgvector."""
    service = KnowledgeService(db)
    success, errors = await service.reindex_all()
    
    return ReindexResponse(
        success_count=success,
        error_count=errors,
        message=f"Reindex: {success} success, {errors} errors"
    )


# =============================================================================
# Search & Stats
# =============================================================================

@router.post("/knowledge/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Search the knowledge base using semantic search."""
    service = KnowledgeService(db)
    results = await service.search_knowledge(
        query=request.query,
        category=request.category,
        top_k=request.top_k
    )
    
    search_results = [
        SearchResult(
            id=r.get("id", ""),
            score=r.get("score", 0),
            title=r.get("metadata", {}).get("title"),
            category=r.get("metadata", {}).get("category"),
            content_preview=truncate_text(r.get("metadata", {}).get("content", ""), 200)
        )
        for r in results
    ]
    
    return SearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results)
    )


@router.get("/knowledge/stats", response_model=KnowledgeStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get knowledge base statistics."""
    service = KnowledgeService(db)
    return await service.get_stats()


@router.get("/knowledge/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get all categories with item counts."""
    service = KnowledgeService(db)
    return {"categories": await service.get_categories()}


# =============================================================================
# Persona Testing
# =============================================================================

@router.post("/persona/test", response_model=PersonaTestResponse)
async def test_persona(
    request: PersonaTestRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Test AI persona response without saving to history."""
    # Parse context type if provided
    context_type = None
    if request.context_type:
        try:
            context_type = ConversationContext(request.context_type)
        except ValueError:
            valid = [c.value for c in ConversationContext]
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid context type. Valid: {valid}"
            )
    
    chat_service = ChatService(db)
    result = await chat_service.test_persona_response(
        test_message=request.message,
        context_type=context_type
    )
    
    return PersonaTestResponse(**result)


@router.get("/persona/context-types")
async def get_context_types(
    admin: dict = Depends(get_current_admin)
):
    """Get available conversation context types."""
    descriptions = {
        ConversationContext.HAIR_EDUCATION: "Hair care and styling advice",
        ConversationContext.BUSINESS_MENTORSHIP: "Business strategy guidance",
        ConversationContext.PRODUCT_RECOMMENDATION: "Product recommendations",
        ConversationContext.TROUBLESHOOTING: "Problem solving",
        ConversationContext.GENERAL: "General conversation"
    }
    
    return {
        "context_types": [
            {"value": ctx.value, "description": descriptions.get(ctx, "")}
            for ctx in ConversationContext
        ]
    }


# =============================================================================
# User Management
# =============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """List all users with optional filtering."""
    user_service = UserService(db)
    
    tier_enum = None
    if tier:
        try:
            tier_enum = UserTier(tier)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid tier. Valid: {[t.value for t in UserTier]}"
            )
    
    users = await user_service.list_users(
        limit=limit,
        offset=offset,
        tier=tier_enum,
        active_only=active_only
    )
    
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get a specific user's details."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Update a user's tier or status."""
    user_service = UserService(db)
    
    tier_enum = None
    if tier:
        try:
            tier_enum = UserTier(tier)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid tier. Valid: {[t.value for t in UserTier]}"
            )
    
    user = await user_service.update_user(
        user_id=user_id,
        tier=tier_enum,
        is_active=is_active,
        is_admin=is_admin
    )
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get a user's chat activity."""
    # Verify user exists
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    # Get chat history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    messages = list(result.scalars().all())
    
    # Get usage stats
    usage_service = UsageService(db)
    usage = await usage_service.get_usage_status(user_id, user.tier.value)
    
    return {
        "user": UserResponse.model_validate(user),
        "usage": usage,
        "recent_messages": [
            {
                "id": m.id,
                "message": truncate_text(m.message, 100),
                "response": truncate_text(m.response, 100) if m.response else None,
                "tokens_used": m.tokens_used,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ],
        "total_messages": len(messages)
    }


@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get a user's usage statistics."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    usage_service = UsageService(db)
    usage = await usage_service.get_usage_status(user_id, user.tier.value)
    
    return usage


# =============================================================================
# System Statistics & Monitoring
# =============================================================================

@router.get("/stats/overview")
async def get_system_overview(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get system-wide statistics overview."""
    user_service = UserService(db)
    
    # User counts
    total_users = await user_service.get_user_count(active_only=False)
    active_users = await user_service.get_user_count(active_only=True)
    users_by_tier = await user_service.get_users_by_tier()
    
    # Message counts
    result = await db.execute(
        select(func.count(ChatMessage.id))
    )
    total_messages = result.scalar() or 0
    
    # Token usage
    result = await db.execute(
        select(func.sum(ChatMessage.tokens_used))
    )
    total_tokens = result.scalar() or 0
    
    # API costs
    result = await db.execute(
        select(func.sum(UsageTracking.api_cost))
    )
    total_cost_micro = result.scalar() or 0
    total_cost_usd = total_cost_micro / 1_000_000
    
    # Messages today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(ChatMessage.id))
        .where(ChatMessage.created_at >= today_start)
    )
    messages_today = result.scalar() or 0
    
    # Messages this week
    week_start = today_start - timedelta(days=today_start.weekday())
    result = await db.execute(
        select(func.count(ChatMessage.id))
        .where(ChatMessage.created_at >= week_start)
    )
    messages_this_week = result.scalar() or 0
    
    # Knowledge base stats
    knowledge_service = KnowledgeService(db)
    kb_stats = await knowledge_service.get_stats()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "by_tier": users_by_tier
        },
        "messages": {
            "total": total_messages,
            "today": messages_today,
            "this_week": messages_this_week
        },
        "tokens": {
            "total_used": total_tokens
        },
        "api_costs": {
            "total_usd": round(total_cost_usd, 4),
            "total_micro_dollars": total_cost_micro
        },
        "knowledge_base": {
            "total_items": kb_stats.total_items,
            "active_items": kb_stats.active_items,
            "categories": kb_stats.categories_count
        }
    }


@router.get("/stats/activity")
async def get_activity_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get activity statistics over time."""
    from sqlalchemy import cast, Date
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Messages per day
    result = await db.execute(
        select(
            cast(ChatMessage.created_at, Date).label('date'),
            func.count(ChatMessage.id).label('count'),
            func.sum(ChatMessage.tokens_used).label('tokens')
        )
        .where(ChatMessage.created_at >= start_date)
        .group_by(cast(ChatMessage.created_at, Date))
        .order_by(cast(ChatMessage.created_at, Date))
    )
    
    daily_stats = [
        {
            "date": str(row.date),
            "messages": row.count,
            "tokens": row.tokens or 0
        }
        for row in result.all()
    ]
    
    # Active users per day
    result = await db.execute(
        select(
            cast(ChatMessage.created_at, Date).label('date'),
            func.count(func.distinct(ChatMessage.user_id)).label('active_users')
        )
        .where(ChatMessage.created_at >= start_date)
        .group_by(cast(ChatMessage.created_at, Date))
        .order_by(cast(ChatMessage.created_at, Date))
    )
    
    active_users_daily = {
        str(row.date): row.active_users
        for row in result.all()
    }
    
    # Merge active users into daily stats
    for stat in daily_stats:
        stat['active_users'] = active_users_daily.get(stat['date'], 0)
    
    return {
        "period_days": days,
        "daily_stats": daily_stats
    }


@router.get("/stats/top-users")
async def get_top_users(
    limit: int = Query(10, ge=1, le=50),
    period_days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get top users by message count."""
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    result = await db.execute(
        select(
            ChatMessage.user_id,
            func.count(ChatMessage.id).label('message_count'),
            func.sum(ChatMessage.tokens_used).label('tokens_used')
        )
        .where(ChatMessage.created_at >= start_date)
        .group_by(ChatMessage.user_id)
        .order_by(desc('message_count'))
        .limit(limit)
    )
    
    top_users_data = result.all()
    
    # Get user details
    user_service = UserService(db)
    top_users = []
    
    for row in top_users_data:
        user = await user_service.get_user_by_id(row.user_id)
        if user:
            top_users.append({
                "user_id": user.id,
                "username": user.username,
                "tier": user.tier.value,
                "message_count": row.message_count,
                "tokens_used": row.tokens_used or 0
            })
    
    return {
        "period_days": period_days,
        "top_users": top_users
    }


# =============================================================================
# Missing KB Items & Question Logging
# =============================================================================

@router.get("/logs/missing-kb", response_model=List[MissingKBItemSchema])
async def list_missing_kb_items(
    unresolved_only: bool = Query(True, description="Show only unresolved items"),
    namespace: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """List missing KB items for weekly review and updates."""
    query = select(MissingKBItem)
    
    if unresolved_only:
        query = query.where(MissingKBItem.is_resolved == False)
    
    if namespace:
        query = query.where(MissingKBItem.suggested_namespace == namespace)
    
    query = query.order_by(desc(MissingKBItem.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return [MissingKBItemSchema.model_validate(item) for item in items]


@router.patch("/logs/missing-kb/{item_id}", response_model=MissingKBItemSchema)
async def update_missing_kb_item(
    item_id: int,
    update: MissingKBItemUpdate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Mark a missing KB item as resolved (e.g., after adding content)."""
    result = await db.execute(select(MissingKBItem).where(MissingKBItem.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Missing KB item not found")
    
    if update.is_resolved is not None:
        item.is_resolved = update.is_resolved
        if update.is_resolved:
            item.resolved_at = datetime.utcnow()
    
    if update.resolved_by_kb_id is not None:
        item.resolved_by_kb_id = update.resolved_by_kb_id
    
    await db.commit()
    await db.refresh(item)
    
    return MissingKBItemSchema.model_validate(item)


@router.get("/logs/missing-kb/stats", response_model=MissingKBStats)
async def get_missing_kb_stats(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get statistics about missing KB items."""
    # Total counts
    result = await db.execute(
        select(func.count(MissingKBItem.id))
        .where(MissingKBItem.is_resolved == False)
    )
    total_unresolved = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(MissingKBItem.id))
        .where(MissingKBItem.is_resolved == True)
    )
    total_resolved = result.scalar() or 0
    
    # By namespace
    result = await db.execute(
        select(
            MissingKBItem.suggested_namespace,
            func.count(MissingKBItem.id).label('count')
        )
        .where(MissingKBItem.is_resolved == False)
        .group_by(MissingKBItem.suggested_namespace)
    )
    by_namespace = {row.suggested_namespace or "unspecified": row.count for row in result.all()}
    
    # Recent items
    result = await db.execute(
        select(MissingKBItem)
        .where(MissingKBItem.is_resolved == False)
        .order_by(desc(MissingKBItem.created_at))
        .limit(10)
    )
    recent_items = [MissingKBItemSchema.model_validate(item) for item in result.scalars().all()]
    
    return MissingKBStats(
        total_unresolved=total_unresolved,
        total_resolved=total_resolved,
        by_namespace=by_namespace,
        recent_items=recent_items
    )


@router.get("/logs/missing-kb/export", response_model=List[MissingKBExport])
async def export_missing_kb_items(
    unresolved_only: bool = Query(True),
    export_format: str = Query("json", regex="^(json|csv)$", alias="format"),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Export missing KB items for Notion/Sheets/Airtable integration."""
    query = select(MissingKBItem)
    
    if unresolved_only:
        query = query.where(MissingKBItem.is_resolved == False)
    
    query = query.order_by(desc(MissingKBItem.created_at))
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    exports = [
        MissingKBExport(
            id=item.id,
            question=item.question,
            missing_detail=item.missing_detail,
            suggested_namespace=item.suggested_namespace,
            user_id=item.user_id,
            is_resolved=item.is_resolved,
            created_at=item.created_at,
            resolved_at=item.resolved_at
        )
        for item in items
    ]
    
    # If CSV format requested, return as CSV string
    if export_format == "csv":
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "question", "missing_detail", "suggested_namespace",
            "user_id", "is_resolved", "created_at", "resolved_at"
        ])
        writer.writeheader()
        
        for item in exports:
            writer.writerow({
                "id": item.id,
                "question": item.question,
                "missing_detail": item.missing_detail,
                "suggested_namespace": item.suggested_namespace or "",
                "user_id": item.user_id,
                "is_resolved": item.is_resolved,
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "resolved_at": item.resolved_at.isoformat() if item.resolved_at else ""
            })
        
        return Response(content=output.getvalue(), media_type="text/csv")
    
    return exports


@router.get("/logs/questions", response_model=List[QuestionLogSchema])
async def list_question_logs(
    category: Optional[str] = None,
    context_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """List question logs for insights and content development."""
    query = select(QuestionLog)
    
    if category:
        query = query.where(QuestionLog.category == category)
    
    if context_type:
        query = query.where(QuestionLog.context_type == context_type)
    
    query = query.order_by(desc(QuestionLog.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return [QuestionLogSchema.model_validate(item) for item in items]


@router.get("/logs/questions/stats", response_model=QuestionStats)
async def get_question_stats(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get statistics about questions asked."""
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Total questions
    result = await db.execute(
        select(func.count(QuestionLog.id))
        .where(QuestionLog.created_at >= start_date)
    )
    total_questions = result.scalar() or 0
    
    # Top questions (by normalized question)
    result = await db.execute(
        select(
            QuestionLog.normalized_question,
            QuestionLog.question,
            func.count(QuestionLog.id).label('count'),
            func.min(QuestionLog.created_at).label('first_asked'),
            func.max(QuestionLog.created_at).label('last_asked')
        )
        .where(QuestionLog.created_at >= start_date)
        .where(QuestionLog.normalized_question.isnot(None))
        .group_by(QuestionLog.normalized_question, QuestionLog.question)
        .order_by(desc('count'))
        .limit(20)
    )
    
    top_questions = [
        {
            "question": row.question,
            "normalized_question": row.normalized_question,
            "count": row.count,
            "first_asked": row.first_asked.isoformat() if row.first_asked else None,
            "last_asked": row.last_asked.isoformat() if row.last_asked else None
        }
        for row in result.all()
    ]
    
    # By category
    result = await db.execute(
        select(
            QuestionLog.category,
            func.count(QuestionLog.id).label('count')
        )
        .where(QuestionLog.created_at >= start_date)
        .where(QuestionLog.category.isnot(None))
        .group_by(QuestionLog.category)
    )
    by_category = {row.category: row.count for row in result.all()}
    
    # By context type
    result = await db.execute(
        select(
            QuestionLog.context_type,
            func.count(QuestionLog.id).label('count')
        )
        .where(QuestionLog.created_at >= start_date)
        .where(QuestionLog.context_type.isnot(None))
        .group_by(QuestionLog.context_type)
    )
    by_context_type = {row.context_type: row.count for row in result.all()}
    
    # Recent questions
    result = await db.execute(
        select(QuestionLog)
        .where(QuestionLog.created_at >= start_date)
        .order_by(desc(QuestionLog.created_at))
        .limit(10)
    )
    recent_questions = [QuestionLogSchema.model_validate(item) for item in result.scalars().all()]
    
    return QuestionStats(
        total_questions=total_questions,
        top_questions=top_questions,
        by_category=by_category,
        by_context_type=by_context_type,
        recent_questions=recent_questions
    )


@router.get("/logs/questions/export", response_model=List[QuestionExport])
async def export_question_logs(
    period_days: int = Query(30, ge=1, le=365),
    export_format: str = Query("json", regex="^(json|csv)$", alias="format"),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Export question logs for insights and content development."""
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Get aggregated questions (by normalized question)
    result = await db.execute(
        select(
            QuestionLog.normalized_question,
            QuestionLog.question,
            QuestionLog.category,
            QuestionLog.context_type,
            QuestionLog.user_tier,
            func.count(QuestionLog.id).label('count'),
            func.min(QuestionLog.created_at).label('first_asked'),
            func.max(QuestionLog.created_at).label('last_asked'),
            func.min(QuestionLog.id).label('sample_id')
        )
        .where(QuestionLog.created_at >= start_date)
        .group_by(
            QuestionLog.normalized_question,
            QuestionLog.question,
            QuestionLog.category,
            QuestionLog.context_type,
            QuestionLog.user_tier
        )
        .order_by(desc('count'))
    )
    
    exports = []
    for row in result.all():
        # Get a sample user_id from one of the logs
        sample_result = await db.execute(
            select(QuestionLog.user_id)
            .where(QuestionLog.id == row.sample_id)
        )
        sample_user_id = sample_result.scalar()
        
        exports.append(
            QuestionExport(
                id=row.sample_id or 0,
                question=row.question or row.normalized_question or "",
                normalized_question=row.normalized_question,
                category=row.category,
                context_type=row.context_type,
                user_id=sample_user_id or 0,
                user_tier=row.user_tier,
                count=row.count,
                first_asked=row.first_asked or datetime.utcnow(),
                last_asked=row.last_asked or datetime.utcnow()
            )
        )
    
    # If CSV format requested, return as CSV string
    if export_format == "csv":
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "question", "normalized_question", "category", "context_type",
            "user_tier", "count", "first_asked", "last_asked"
        ])
        writer.writeheader()
        
        for item in exports:
            writer.writerow({
                "question": item.question,
                "normalized_question": item.normalized_question or "",
                "category": item.category or "",
                "context_type": item.context_type or "",
                "user_tier": item.user_tier or "",
                "count": item.count,
                "first_asked": item.first_asked.isoformat() if item.first_asked else "",
                "last_asked": item.last_asked.isoformat() if item.last_asked else ""
            })
        
        return Response(content=output.getvalue(), media_type="text/csv")
    
    return exports


@router.get("/logs/stats", response_model=LoggingStatsResponse)
async def get_all_logging_stats(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get comprehensive logging statistics for dashboard."""
    # Missing KB stats
    missing_kb_result = await get_missing_kb_stats(db=db, admin=admin)
    
    # Question stats
    question_result = await get_question_stats(period_days=period_days, db=db, admin=admin)
    
    return LoggingStatsResponse(
        missing_kb=missing_kb_result,
        questions=question_result
    )

