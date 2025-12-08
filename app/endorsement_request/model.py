"""Endorsement request SQLAlchemy model"""

from datetime import date
from typing import Any

from app.employer import model as employer_model  # noqa: F401
from app.ledger_transaction import model as ledger_transaction_model  # noqa: F401

from sqlalchemy import String, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EndorsementRequest(Base):
    """Endorsement request model - tracks lifecycle of change requests"""

    __tablename__ = "endorsement_requests"

    employer_id: Mapped[str] = mapped_column(
        String(17),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # ADDITION, DELETION, MODIFICATION
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # RECEIVED, VALIDATED, FUNDS_LOCKED, SENT, COMPLETED, FAILED, ON_HOLD
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

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
