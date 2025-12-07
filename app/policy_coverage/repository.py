"""Policy coverage repository"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.base.repository import BaseRepository
from app.policy_coverage.model import PolicyCoverage


class PolicyCoverageRepository(BaseRepository[PolicyCoverage]):
    """Repository for PolicyCoverage entity"""

    def __init__(self, session: AsyncSession):
        """Initialize policy coverage repository"""
        super().__init__(PolicyCoverage, session)

    async def get_by_employee_id(
        self, employee_id: str, skip: int = 0, limit: int = 100
    ) -> list[PolicyCoverage]:
        """
        Get all policy coverages for an employee.

        Args:
            employee_id: Employee ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of policy coverage instances
        """
        query = (
            select(self.model)
            .where(self.model.employee_id == employee_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_by_employee_id(self, employee_id: str) -> list[PolicyCoverage]:
        """
        Get active policy coverages for an employee.

        Args:
            employee_id: Employee ID

        Returns:
            List of active policy coverage instances
        """
        query = select(self.model).where(
            and_(
                self.model.employee_id == employee_id,
                self.model.status == "ACTIVE",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_insurer_id(
        self, insurer_id: str, skip: int = 0, limit: int = 100
    ) -> list[PolicyCoverage]:
        """
        Get all policy coverages for an insurer.

        Args:
            insurer_id: Insurer ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of policy coverage instances
        """
        query = (
            select(self.model)
            .where(self.model.insurer_id == insurer_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self, start_date: date, end_date: date, skip: int = 0, limit: int = 100
    ) -> list[PolicyCoverage]:
        """
        Get policy coverages active in a date range.

        Args:
            start_date: Start date
            end_date: End date
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of policy coverage instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.start_date <= end_date,
                    (self.model.end_date >= start_date) | (self.model.end_date.is_(None)),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
