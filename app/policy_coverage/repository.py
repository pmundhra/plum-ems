"""Policy coverage repository"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.base.repository import BaseRepository
from app.policy_coverage.model import PolicyCoverage


class PolicyCoverageRepository(BaseRepository[PolicyCoverage]):
    """Repository for PolicyCoverage entity - all methods scoped by employer_id"""

    def __init__(self, session: AsyncSession):
        """Initialize policy coverage repository"""
        super().__init__(PolicyCoverage, session)

    async def get_by_employee_id(
        self, employer_id: str, employee_id: str, skip: int = 0, limit: int = 100
    ) -> list[PolicyCoverage]:
        """
        Get all policy coverages for an employee, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
            employee_id: Employee ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of policy coverage instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.employer_id == employer_id,
                    self.model.employee_id == employee_id,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_by_employee_id(
        self, employer_id: str, employee_id: str
    ) -> list[PolicyCoverage]:
        """
        Get active policy coverages for an employee, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
            employee_id: Employee ID

        Returns:
            List of active policy coverage instances
        """
        query = select(self.model).where(
            and_(
                self.model.employer_id == employer_id,
                self.model.employee_id == employee_id,
                self.model.status == "ACTIVE",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_insurer_id(
        self, employer_id: str, insurer_id: str, skip: int = 0, limit: int = 100
    ) -> list[PolicyCoverage]:
        """
        Get all policy coverages for an insurer, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
            insurer_id: Insurer ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of policy coverage instances
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.employer_id == employer_id,
                    self.model.insurer_id == insurer_id,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        employer_id: str,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PolicyCoverage]:
        """
        Get policy coverages active in a date range, scoped by employer_id.

        Args:
            employer_id: Employer ID (required for security scoping)
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
                    self.model.employer_id == employer_id,
                    self.model.start_date <= end_date,
                    (self.model.end_date >= start_date) | (self.model.end_date.is_(None)),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
