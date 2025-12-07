"""Employer repository"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.base.repository import BaseRepository
from app.employer.model import Employer


class EmployerRepository(BaseRepository[Employer]):
    """Repository for Employer entity"""

    def __init__(self, session: AsyncSession):
        """Initialize employer repository"""
        super().__init__(Employer, session)

    async def get_by_name(self, name: str) -> Employer | None:
        """
        Get employer by name.

        Args:
            name: Employer name

        Returns:
            Employer instance or None
        """
        query = select(self.model).where(self.model.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_balance(
        self, employer_id: str, new_balance: Any
    ) -> Employer | None:
        """
        Update employer's EA balance.

        Args:
            employer_id: Employer ID
            new_balance: New balance value

        Returns:
            Updated employer instance or None
        """
        return await self.update(employer_id, ea_balance=new_balance)
