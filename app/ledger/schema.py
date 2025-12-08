"""Ledger request and response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LedgerBalanceResponse(BaseModel):
    """Response payload for ledger balance queries."""

    employer_id: str = Field(..., description="Employer identifier")
    employer_name: str = Field(..., description="Employer legal name")
    currency: str = Field(..., description="Currency code for the balances")
    available_balance: Decimal = Field(..., description="Available funds for new transactions")
    locked_funds: Decimal = Field(..., description="Funds reserved for pending endorsements")
    total_balance: Decimal = Field(..., description="Sum of available and locked funds")
    low_balance_threshold: Decimal = Field(
        ..., description="Configured low balance alert threshold"
    )
    status: str = Field(..., description="Overall ledger status (e.g., ACTIVE, LOW_BALANCE)")
    allowed_overdraft: bool = Field(..., description="Whether overdraft is permitted")

    class Config:
        from_attributes = True


class LedgerTopUpRequest(BaseModel):
    """Payload for crediting an employer's endorsement account."""

    employer_id: str = Field(..., description="Employer identifier")
    transaction_reference: str = Field(..., description="External payment reference")
    amount: Decimal = Field(..., gt=0, description="Top-up amount in the specified currency")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    payment_method: str = Field(..., description="Payment method or gateway name")
    timestamp: datetime = Field(
        ..., description="Timestamp when the payment was processed or received"
    )


class LedgerTopUpResponse(BaseModel):
    """Response returned after a successful top-up."""

    transaction_id: str = Field(..., description="Internal ledger transaction ID")
    employer_id: str = Field(..., description="Employer identifier")
    transaction_reference: str = Field(..., description="External payment reference")
    amount: Decimal = Field(..., description="Credited amount")
    currency: str = Field(..., description="Currency for the credited amount")
    payment_method: str = Field(..., description="Payment method or gateway name")
    timestamp: datetime = Field(..., description="Timestamp supplied by the caller")
    status: str = Field(..., description="Transaction status (e.g., CLEARED)")
    new_balance: Decimal = Field(..., description="Employer balance after the top-up")

    class Config:
        from_attributes = True


class LedgerTransactionHistoryItem(BaseModel):
    """History item for ledger transactions."""

    id: str = Field(..., description="Ledger transaction identifier")
    employer_id: str = Field(..., description="Employer identifier")
    date: datetime = Field(..., description="Timestamp when the transaction was recorded")
    type: str = Field(..., description="Transaction direction (CREDIT/DEBIT)")
    amount: Decimal = Field(..., description="Signed amount (DEBITs are negative)")
    status: str = Field(..., description="Transaction status")
    description: str = Field(..., description="Human readable description")
    external_reference: str | None = Field(
        None, description="External payment/transaction identifier"
    )
    endorsement_id: str | None = Field(
        None, description="Linked endorsement request, if any"
    )

    class Config:
        from_attributes = True
