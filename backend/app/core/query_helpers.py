"""
Database Query Helpers

Common query patterns and optimizations to reduce duplication.
"""
from typing import Optional, TypeVar, Type, List
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.performance import optimize_query
from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class QueryBuilder:
    """Helper class for building optimized database queries."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
        self._query = select(model)
    
    def filter_by(self, **filters) -> "QueryBuilder":
        """Add WHERE clauses to query."""
        for key, value in filters.items():
            if value is not None:
                if hasattr(self.model, key):
                    self._query = self._query.where(
                        getattr(self.model, key) == value
                    )
        return self
    
    def order_by(self, field: str, descending: bool = True) -> "QueryBuilder":
        """Add ORDER BY clause."""
        if hasattr(self.model, field):
            if descending:
                self._query = self._query.order_by(desc(getattr(self.model, field)))
            else:
                self._query = self._query.order_by(asc(getattr(self.model, field)))
        return self
    
    def paginate(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> "QueryBuilder":
        """Add pagination to query."""
        limit = min(limit or DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT)
        offset = offset or 0
        self._query = optimize_query(self._query, limit=limit, offset=offset)
        return self
    
    def build(self):
        """Return the final query."""
        return self._query


async def get_paginated_results(
    db: AsyncSession,
    model: Type[ModelType],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    filters: Optional[dict] = None,
    order_by: Optional[str] = None,
    descending: bool = True
) -> List[ModelType]:
    """
    Get paginated results with common patterns.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        limit: Maximum results
        offset: Pagination offset
        filters: Dictionary of field:value filters
        order_by: Field to order by
        descending: Order direction
    
    Returns:
        List of model instances
    """
    builder = QueryBuilder(model, db)
    
    if filters:
        builder.filter_by(**filters)
    
    if order_by:
        builder.order_by(order_by, descending)
    
    builder.paginate(limit, offset)
    
    result = await db.execute(builder.build())
    return list(result.scalars().all())


async def count_records(
    db: AsyncSession,
    model: Type[ModelType],
    filters: Optional[dict] = None
) -> int:
    """
    Count records matching filters.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        filters: Dictionary of field:value filters
    
    Returns:
        Count of matching records
    """
    query = select(func.count(model.id))
    
    if filters:
        for key, value in filters.items():
            if value is not None and hasattr(model, key):
                query = query.where(getattr(model, key) == value)
    
    result = await db.execute(query)
    return result.scalar() or 0
