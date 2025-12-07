"""Employee SQLAlchemy model"""

from typing import Any

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Employee(Base):
    """Employee model - stores census data"""

    __tablename__ = "employees"

    employer_id: Mapped[str] = mapped_column(
        String(17),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    demographics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Relationships
    employer = relationship("Employer", back_populates="employees")
    policy_coverages = relationship(
        "PolicyCoverage", back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, employee_code={self.employee_code}, employer_id={self.employer_id})>"
