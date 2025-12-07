"""Employee SQLAlchemy model"""

from typing import Any
from uuid import UUID

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Employee(Base):
    """Employee model - stores census data"""

    __tablename__ = "employees"

    id: UUID = Column(PGUUID(as_uuid=True), primary_key=True, index=True)
    employer_id: UUID = Column(
        PGUUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_code: str = Column(String(50), nullable=False, index=True)
    demographics: dict[str, Any] = Column(JSONB, nullable=False)

    # Relationships
    employer = relationship("Employer", back_populates="employees")
    policy_coverages = relationship(
        "PolicyCoverage", back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, employee_code={self.employee_code}, employer_id={self.employer_id})>"
