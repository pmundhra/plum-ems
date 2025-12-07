"""Ledger transaction SQLAlchemy model"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class LedgerTransaction(Base):
    """Ledger transaction model - financial audit trail (immutable)"""

    __tablename__ = "ledger_transactions"

    id: UUID = Column(PGUUID(as_uuid=True), primary_key=True, index=True)
    employer_id: UUID = Column(
        PGUUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endorsement_id: UUID | None = Column(
        PGUUID(as_uuid=True),
        ForeignKey("endorsement_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: str = Column(String(20), nullable=False, index=True)  # DEBIT, CREDIT
    amount: Decimal = Column(Numeric(15, 2), nullable=False)
    status: str = Column(
        String(20), nullable=False, index=True
    )  # LOCKED, CLEARED, FAILED, PENDING
    external_ref: str | None = Column(String(100), nullable=True, index=True)

    # Relationships
    employer = relationship("Employer", back_populates="ledger_transactions")
    endorsement_request = relationship("EndorsementRequest", back_populates="ledger_transactions")

    def __repr__(self) -> str:
        return (
            f"<LedgerTransaction(id={self.id}, type={self.type}, "
            f"amount={self.amount}, status={self.status})>"
        )
