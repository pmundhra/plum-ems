"""Endorsement request repository"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.base.repository import BaseRepository
from app.endorsement_request.model import EndorsementRequest


class EndorsementRequestRepository(BaseRepository[EndorsementRequest]):
    """Repository for EndorsementRequest entity"""

    def __init__(self, session: AsyncSession):
        """Initialize endorsement request repository"""
        super().__init__(EndorsementRequest, session)

    async def get_by_employer_id(
        self, employer_id: str, skip: int = 0, limit: int = 100
    ) -> list[EndorsementRequest]:
        """
        Get all endorsement requests for an employer.

        Args:
            employer_id: Employer ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of endorsement request instances
        """
        query = (
            select(self.model)
            .where(self.model.employer_id == employer_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[EndorsementRequest]:
        """
        Get endorsement requests by status.

        Args:
            status: Request status
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of endorsement request instances
        """
        query = (
            select(self.model)
            .where(self.model.status == status)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_type(
        self, type: str, skip: int = 0, limit: int = 100
    ) -> list[EndorsementRequest]:
        """
        Get endorsement requests by type.

        Args:
            type: Request type (ADDITION, DELETION, MODIFICATION)
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of endorsement request instances
        """
        query = (
            select(self.model)
            .where(self.model.type == type)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_on_hold_by_employer_id(self, employer_id: str) -> list[EndorsementRequest]:
        """
        Get all ON_HOLD_FUNDS endorsement requests for an employer.

        Args:
            employer_id: Employer ID

        Returns:
            List of on-hold endorsement request instances
        """
        query = select(self.model).where(
            and_(
                self.model.employer_id == employer_id,
                self.model.status == "ON_HOLD",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_effective_date(
        self, effective_date: date, skip: int = 0, limit: int = 100
    ) -> list[EndorsementRequest]:
        """
        Get endorsement requests by effective date.

        Args:
            effective_date: Effective date
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of endorsement request instances
        """
        query = (
            select(self.model)
            .where(self.model.effective_date == effective_date)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
