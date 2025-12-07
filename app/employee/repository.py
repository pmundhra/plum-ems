"""Employee repository"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.base.repository import BaseRepository
from app.employee.model import Employee


class EmployeeRepository(BaseRepository[Employee]):
    """Repository for Employee entity"""

    def __init__(self, session: AsyncSession):
        """Initialize employee repository"""
        super().__init__(Employee, session)

    async def get_by_employer_id(
        self, employer_id: str, skip: int = 0, limit: int = 100
    ) -> list[Employee]:
        """
        Get all employees for an employer.

        Args:
            employer_id: Employer ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of employee instances
        """
        query = (
            select(self.model)
            .where(self.model.employer_id == employer_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_employee_code(
        self, employer_id: str, employee_code: str
    ) -> Employee | None:
        """
        Get employee by employer ID and employee code.

        Args:
            employer_id: Employer ID
            employee_code: Employee code

        Returns:
            Employee instance or None
        """
        query = select(self.model).where(
            self.model.employer_id == employer_id,
            self.model.employee_code == employee_code,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
