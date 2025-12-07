"""Ledger transaction SQLAlchemy model"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LedgerTransaction(Base):
    """Ledger transaction model - financial audit trail (immutable)"""

    __tablename__ = "ledger_transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, index=True)
    employer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endorsement_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("endorsement_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # DEBIT, CREDIT
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # LOCKED, CLEARED, FAILED, PENDING
    external_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    employer = relationship("Employer", back_populates="ledger_transactions")
    endorsement_request = relationship("EndorsementRequest", back_populates="ledger_transactions")

    def __repr__(self) -> str:
        return (
            f"<LedgerTransaction(id={self.id}, type={self.type}, "
            f"amount={self.amount}, status={self.status})>"
        )
