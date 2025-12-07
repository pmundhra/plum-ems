"""Policy coverage SQLAlchemy model"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PolicyCoverage(Base):
    """Policy coverage model - tracks insurance coverage span for an employee"""

    __tablename__ = "policy_coverages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, index=True)
    employee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insurer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # ACTIVE, INACTIVE, PENDING_ISSUANCE
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    plan_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="policy_coverages")

    def __repr__(self) -> str:
        return (
            f"<PolicyCoverage(id={self.id}, employee_id={self.employee_id}, "
            f"insurer_id={self.insurer_id}, status={self.status})>"
        )
