"""
Base Service Class

Provides common functionality for all service classes:
- Database session management
- Logging
- Error handling utilities

All domain services should inherit from BaseService.
"""
import logging
from typing import TypeVar, Generic, Optional, Type, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase

from app.core.exceptions import NotFoundError

# Generic type for models
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseService(Generic[ModelType]):
    """
    Base service class with common CRUD operations.
    
    Provides:
    - Database session access
    - Logger instance
    - Common query methods
    
    Usage:
        class UserService(BaseService[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(db, User, "UserService")
    """
    
    def __init__(
        self,
        db: AsyncSession,
        model: Optional[Type[ModelType]] = None,
        logger_name: Optional[str] = None
    ):
        """
        Initialize the service.
        
        Args:
            db: Async database session
            model: SQLAlchemy model class (optional)
            logger_name: Name for the logger (defaults to class name)
        """
        self.db = db
        self.model = model
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)
    
    # =========================================================================
    # Common Query Methods
    # =========================================================================
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None
        """
        if not self.model:
            raise NotImplementedError("Model not set for this service")
        
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_or_raise(self, id: int, resource_name: str = "Resource") -> ModelType:
        """
        Get a record by ID or raise NotFoundError.
        
        Args:
            id: Primary key value
            resource_name: Name for error message
            
        Returns:
            Model instance
            
        Raises:
            NotFoundError: If record not found
        """
        result = await self.get_by_id(id)
        if not result:
            raise NotFoundError(resource_name, id)
        return result
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            order_by: Column to order by
            
        Returns:
            List of model instances
        """
        if not self.model:
            raise NotImplementedError("Model not set for this service")
        
        query = select(self.model)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(self, **filters) -> int:
        """
        Count records with optional filters.
        
        Args:
            **filters: Field=value filters
            
        Returns:
            Count of matching records
        """
        if not self.model:
            raise NotImplementedError("Model not set for this service")
        
        query = select(func.count(self.model.id))
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        return await self.get_by_id(id) is not None
    
    # =========================================================================
    # Common Write Methods
    # =========================================================================
    
    async def create(self, **data) -> ModelType:
        """
        Create a new record.
        
        Args:
            **data: Field values for the new record
            
        Returns:
            Created model instance
        """
        if not self.model:
            raise NotImplementedError("Model not set for this service")
        
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        
        self.logger.info(f"Created {self.model.__name__} with id {instance.id}")
        return instance
    
    async def update(self, id: int, **data) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            id: Primary key value
            **data: Fields to update
            
        Returns:
            Updated model instance or None
        """
        instance = await self.get_by_id(id)
        if not instance:
            return None
        
        for field, value in data.items():
            if value is not None and hasattr(instance, field):
                setattr(instance, field, value)
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        self.logger.info(f"Updated {self.model.__name__} with id {id}")
        return instance
    
    async def delete(self, id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False
        
        await self.db.delete(instance)
        await self.db.commit()
        
        self.logger.info(f"Deleted {self.model.__name__} with id {id}")
        return True
    
    # =========================================================================
    # Transaction Helpers
    # =========================================================================
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.db.rollback()
    
    async def refresh(self, instance: ModelType) -> None:
        """Refresh an instance from the database."""
        await self.db.refresh(instance)
