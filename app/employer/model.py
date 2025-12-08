"""Employer SQLAlchemy model"""

from decimal import Decimal
from typing import Any

from sqlalchemy import String, Numeric, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.employee import model as employee_model  # noqa: F401
from app.endorsement_request import model as endorsement_request_model  # noqa: F401
from app.ledger_transaction import model as ledger_transaction_model  # noqa: F401


class Employer(Base):
    """Employer model - stores master data for group policyholders"""

    __tablename__ = "employers"

    employer_id: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ea_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0.00"), nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="employer", cascade="all, delete-orphan")
    endorsement_requests = relationship(
        "EndorsementRequest", back_populates="employer", cascade="all, delete-orphan"
    )
    ledger_transactions = relationship(
        "LedgerTransaction", back_populates="employer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employer(id={self.id}, employer_id={self.employer_id}, name={self.name}, status={self.status})>"


@event.listens_for(Employer, "before_insert", propagate=True)
@event.listens_for(Employer, "before_update", propagate=True)
def _set_employer_id(mapper, connection, target):
    """
    Ensure employer_id is always set to id for Employer model.
    This event listener runs before insert/update to keep employer_id in sync with id.
    """
    # Generate ID if not set (for inserts, the default lambda might not have been called yet)
    if not target.id:
        from app.utils.id_generator import _generate_id
        target.id = _generate_id()
    
    # Set employer_id to match id (always sync employer_id with id)
    target.employer_id = target.id
