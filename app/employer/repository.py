"""Employer repository"""

from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base.repository import BaseRepository
from app.employer.model import Employer


class EmployerRepository(BaseRepository[Employer]):
    """Repository for Employer entity - all methods scoped by employer_id (using id field)"""

    def __init__(self, session: AsyncSession):
        """Initialize employer repository"""
        super().__init__(Employer, session)

    async def get_by_id_unscoped(self, id: str) -> Employer | None:
        """
        Get employer by ID without employer_id scoping (for top-level entity).

        Args:
            id: Employer ID

        Returns:
            Employer instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, id: str) -> Employer | None:
        """
        Lock the employer row using FOR UPDATE to ensure ACID balance adjustments.
        """
        query = select(self.model).where(self.model.id == id).with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_unscoped(
        self, skip: int = 0, limit: int = 100
    ) -> list[Employer]:
        """
        Get all employers with pagination without employer_id scoping.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of employer instances
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_unscoped(self) -> int:
        """
        Count all employers without employer_id scoping.

        Returns:
            Total count of employers
        """
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update_unscoped(self, id: str, **kwargs: Any) -> Employer | None:
        """
        Update employer by ID without employer_id scoping.

        Args:
            id: Employer ID
            **kwargs: Attributes to update

        Returns:
            Updated employer instance or None if not found
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_by_id_unscoped(id)

    async def get_by_name(self, employer_id: str, name: str) -> Employer | None:
        """
        Get employer by name, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
            name: Employer name

        Returns:
            Employer instance or None if not found or doesn't match employer_id
        """
        query = select(self.model).where(
            self.model.id == employer_id,
            self.model.name == name,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_balance(
        self, employer_id: str, new_balance: Any
    ) -> Employer | None:
        """
        Update employer's EA balance, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
            new_balance: New balance value

        Returns:
            Updated employer instance or None
        """
        return await super().update(employer_id, employer_id=employer_id, ea_balance=new_balance)

