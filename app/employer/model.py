"""Employer SQLAlchemy model"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Employer(Base):
    """Employer model - stores master data for group policyholders"""

    __tablename__ = "employers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, index=True)
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
        return f"<Employer(id={self.id}, name={self.name}, status={self.status})>"
