"""Employer SQLAlchemy model"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Column, String, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Employer(Base):
    """Employer model - stores master data for group policyholders"""

    __tablename__ = "employers"

    id: UUID = Column(PGUUID(as_uuid=True), primary_key=True, index=True)
    name: str = Column(String(255), nullable=False)
    ea_balance: Decimal = Column(
        Numeric(15, 2), default=Decimal("0.00"), nullable=False
    )
    config: dict[str, Any] = Column(JSONB, nullable=False)
    status: str = Column(String(20), default="ACTIVE", nullable=False)

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
