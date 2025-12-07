"""Base repository classes for common CRUD operations"""

from typing import Generic, TypeVar, Type, Any, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get_by_id(
        self, id: str, load_relationships: list[str] | None = None
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            id: Record ID
            load_relationships: Optional list of relationship names to eager load

        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)

        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        load_relationships: list[str] | None = None,
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: Optional list of relationship names to eager load

        Returns:
            List of model instances
        """
        query = select(self.model).offset(skip).limit(limit)

        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model attributes

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: str, **kwargs: Any) -> Optional[ModelType]:
        """
        Update a record by ID.

        Args:
            id: Record ID
            **kwargs: Attributes to update

        Returns:
            Updated model instance or None if not found
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: str) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, **filters: Any) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Filter criteria (attribute=value)

        Returns:
            Count of matching records
        """
        query = select(self.model)

        for attr, value in filters.items():
            if hasattr(self.model, attr):
                query = query.where(getattr(self.model, attr) == value)

        # Build count query
        count_query = select(func.count()).select_from(query.subquery())
        result = await self.session.execute(count_query)
        return result.scalar() or 0

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record ID

        Returns:
            True if exists, False otherwise
        """
        instance = await self.get_by_id(id)
        return instance is not None
