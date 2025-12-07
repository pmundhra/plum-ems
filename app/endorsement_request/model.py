"""Endorsement request SQLAlchemy model"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class EndorsementRequest(Base):
    """Endorsement request model - tracks lifecycle of change requests"""

    __tablename__ = "endorsement_requests"

    id: UUID = Column(PGUUID(as_uuid=True), primary_key=True, index=True)
    employer_id: UUID = Column(
        PGUUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: str = Column(String(20), nullable=False, index=True)  # ADDITION, DELETION, MODIFICATION
    status: str = Column(
        String(30), nullable=False, index=True
    )  # RECEIVED, VALIDATED, FUNDS_LOCKED, SENT, COMPLETED, FAILED, ON_HOLD
    payload: dict[str, Any] = Column(JSONB, nullable=False)
    retry_count: int = Column(Integer, default=0, nullable=False)
    effective_date: date = Column(Date, nullable=False, index=True)
    trace_id: str | None = Column(String(64), nullable=True, index=True)

    # Relationships
    employer = relationship("Employer", back_populates="endorsement_requests")
    ledger_transactions = relationship(
        "LedgerTransaction", back_populates="endorsement_request"
    )

    def __repr__(self) -> str:
        return (
            f"<EndorsementRequest(id={self.id}, type={self.type}, "
            f"status={self.status}, employer_id={self.employer_id})>"
        )
