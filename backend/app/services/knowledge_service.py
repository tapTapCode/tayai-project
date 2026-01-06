"""
Knowledge Service - Business logic for knowledge base operations.

Handles:
1. Creating and managing knowledge base items
2. Syncing content with PostgreSQL pgvector
3. Bulk upload and processing operations
4. Category management
"""
import json
import logging
from typing import List, Optional, Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import KnowledgeBase
from app.schemas.knowledge import (
    KnowledgeBaseItem,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    BulkUploadResult,
    KnowledgeStats
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for knowledge base operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_service = RAGService(db=db)
    
    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------
    
    async def create_knowledge_item(
        self,
        item: KnowledgeBaseCreate
    ) -> KnowledgeBaseItem:
        """Create a new knowledge base item and index in PostgreSQL pgvector."""
        # Create database record
        db_item = KnowledgeBase(
            title=item.title,
            content=item.content,
            category=item.category,
            extra_metadata=json.dumps(item.metadata) if item.metadata else None
        )
        self.db.add(db_item)
        await self.db.commit()
        await self.db.refresh(db_item)
        
        # Index in PostgreSQL pgvector
        content_id = f"kb_{db_item.id}"
        success, chunk_ids = await self.rag_service.index_content(
            content=item.content,
            metadata={
                "title": item.title,
                "category": item.category or "",
                "id": db_item.id,
                "source": "knowledge_base"
            },
            content_id=content_id,
            chunk_content=True,
            knowledge_base_id=db_item.id
        )
        
        if not success:
            logger.warning(f"Failed to index item {db_item.id}")
        
        db_item.vector_id = content_id
        await self.db.commit()
        await self.db.refresh(db_item)
        
        logger.info(f"Created item {db_item.id} with {len(chunk_ids)} chunks")
        return self._to_schema(db_item)
    
    async def get_knowledge_item(self, item_id: int) -> Optional[KnowledgeBaseItem]:
        """Get a single knowledge base item by ID."""
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == item_id)
        )
        item = result.scalar_one_or_none()
        return self._to_schema(item) if item else None
    
    async def update_knowledge_item(
        self,
        item_id: int,
        update: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBaseItem]:
        """Update an existing knowledge base item."""
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == item_id)
        )
        db_item = result.scalar_one_or_none()
        
        if not db_item:
            return None
        
        content_changed = False
        
        if update.title is not None:
            db_item.title = update.title
            content_changed = True
        
        if update.content is not None:
            db_item.content = update.content
            content_changed = True
        
        if update.category is not None:
            db_item.category = update.category
            content_changed = True
        
        if update.metadata is not None:
            db_item.extra_metadata = json.dumps(update.metadata)
        
        if update.is_active is not None:
            db_item.is_active = update.is_active
        
        await self.db.commit()
        await self.db.refresh(db_item)
        
        # Re-index if content changed
        content_id = db_item.vector_id or f"kb_{db_item.id}"
        if content_changed:
            await self.rag_service.update_content(
                content=db_item.content,
                metadata={
                    "title": db_item.title,
                    "category": db_item.category or "",
                    "id": db_item.id,
                    "source": "knowledge_base"
                },
                content_id=content_id,
                knowledge_base_id=db_item.id
            )
            db_item.vector_id = content_id
            await self.db.commit()
            logger.info(f"Re-indexed item {item_id}")
        
        return self._to_schema(db_item)
    
    async def delete_knowledge_item(self, item_id: int) -> bool:
        """Delete a knowledge base item from DB and PostgreSQL pgvector."""
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == item_id)
        )
        db_item = result.scalar_one_or_none()
        
        if not db_item:
            return False
        
        content_id = db_item.vector_id or f"kb_{db_item.id}"
        await self.rag_service.delete_content(content_id)
        
        await self.db.delete(db_item)
        await self.db.commit()
        
        logger.info(f"Deleted item {item_id}")
        return True
    
    async def list_knowledge_items(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[KnowledgeBaseItem]:
        """List knowledge base items with optional filtering."""
        query = select(KnowledgeBase)
        
        if active_only:
            query = query.where(KnowledgeBase.is_active == True)
        
        if category:
            query = query.where(KnowledgeBase.category == category)
        
        query = query.order_by(KnowledgeBase.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return [self._to_schema(item) for item in result.scalars().all()]
    
    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------
    
    async def bulk_create(self, items: List[KnowledgeBaseCreate]) -> BulkUploadResult:
        """Create multiple knowledge base items."""
        success_count = 0
        error_count = 0
        errors = []
        created_ids = []
        
        for i, item in enumerate(items):
            try:
                created = await self.create_knowledge_item(item)
                created_ids.append(created.id)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"index": i, "title": item.title, "error": str(e)})
                logger.error(f"Error creating '{item.title}': {e}")
        
        logger.info(f"Bulk create: {success_count} success, {error_count} errors")
        
        return BulkUploadResult(
            total=len(items),
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            created_ids=created_ids
        )
    
    async def reindex_all(self) -> Tuple[int, int]:
        """Reindex all knowledge base items in PostgreSQL pgvector."""
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.is_active == True)
        )
        items = result.scalars().all()
        
        success_count = 0
        error_count = 0
        
        for item in items:
            try:
                content_id = f"kb_{item.id}"
                success, _ = await self.rag_service.index_content(
                    content=item.content,
                    metadata={
                        "title": item.title,
                        "category": item.category or "",
                        "id": item.id,
                        "source": "knowledge_base"
                    },
                    content_id=content_id,
                    chunk_content=True,
                    knowledge_base_id=item.id
                )
                
                if success:
                    item.vector_id = content_id
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error reindexing item {item.id}: {e}")
                error_count += 1
        
        await self.db.commit()
        logger.info(f"Reindex: {success_count} success, {error_count} errors")
        
        return success_count, error_count
    
    # -------------------------------------------------------------------------
    # Statistics & Search
    # -------------------------------------------------------------------------
    
    async def get_categories(self) -> List[Dict]:
        """Get all categories with item counts."""
        result = await self.db.execute(
            select(
                KnowledgeBase.category,
                func.count(KnowledgeBase.id).label("count")
            )
            .where(KnowledgeBase.is_active == True)
            .group_by(KnowledgeBase.category)
        )
        
        return [
            {"category": row.category or "uncategorized", "count": row.count}
            for row in result
        ]
    
    async def get_stats(self) -> KnowledgeStats:
        """Get statistics about the knowledge base."""
        total = (await self.db.execute(
            select(func.count(KnowledgeBase.id))
        )).scalar()
        
        active = (await self.db.execute(
            select(func.count(KnowledgeBase.id))
            .where(KnowledgeBase.is_active == True)
        )).scalar()
        
        categories = await self.get_categories()
        
        try:
            index_stats = await self.rag_service.get_index_stats()
        except Exception as e:
            logger.warning(f"Could not get index stats: {e}")
            index_stats = {}
        
        return KnowledgeStats(
            total_items=total,
            active_items=active,
            categories=categories,
            vector_count=index_stats.get("total_vectors", 0),
            index_dimension=index_stats.get("dimension", 0)
        )
    
    async def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """Search knowledge base using semantic search."""
        filter_metadata = {"category": category} if category else None
        
        return await self.rag_service.search_similar(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
    
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    
    def _to_schema(self, db_item: KnowledgeBase) -> KnowledgeBaseItem:
        """Convert database model to schema."""
        return KnowledgeBaseItem(
            id=db_item.id,
            title=db_item.title,
            content=db_item.content,
            category=db_item.category,
            metadata=db_item.extra_metadata,
            is_active=db_item.is_active,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at
        )
