"\"\"\"Ledger API endpoints\"\"\""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, Security
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, ResourceNotFoundError
from app.core.metrics import LEDGER_BALANCE
from app.core.security.jwt import get_current_user
from app.core.settings import settings
from app.employer.model import Employer
from app.employer.repository import EmployerRepository
from app.ledger.schema import (
    LedgerBalanceResponse,
    LedgerTopUpRequest,
    LedgerTopUpResponse,
    LedgerTransactionHistoryItem,
)
from app.ledger_transaction.model import LedgerTransaction
from app.schemas.pagination import PaginatedResponse, build_link_header

router = APIRouter(prefix="/ledger", tags=["Ledger v1"])

LOCKED_DEBIT_STATUSES = {"LOCKED", "ON_HOLD_FUNDS", "ON_HOLD"}


def _resolve_employer_scope(
    requested_employer_id: str | None, current_user: dict[str, Any]
) -> str | None:
    user_employer_id = current_user.get("employer_id")
    if user_employer_id:
        if requested_employer_id and requested_employer_id != user_employer_id:
            raise ForbiddenError("Access denied. You can only query your own employer.")
        return user_employer_id
    return requested_employer_id


def _build_balance_item(
    employer: Employer, locked_amount: Decimal | None
) -> LedgerBalanceResponse:
    locked = Decimal(locked_amount or Decimal("0"))
    available = employer.ea_balance or Decimal("0")
    config = employer.config or {}
    threshold = Decimal(
        str(
            config.get("low_balance_threshold")
            or settings.LEDGER_LOW_BALANCE_THRESHOLD
        )
    )
    total = available + locked
    allowed_overdraft = bool(config.get("allowed_overdraft"))
    status = (employer.status or "UNKNOWN").upper()
    if available < threshold:
        status = "LOW_BALANCE"

    return LedgerBalanceResponse(
        employer_id=employer.id,
        employer_name=employer.name,
        currency=settings.LEDGER_CURRENCY,
        available_balance=available,
        locked_funds=locked,
        total_balance=total,
        low_balance_threshold=threshold,
        status=status,
        allowed_overdraft=allowed_overdraft,
    )


def _build_history_item(transaction: LedgerTransaction) -> LedgerTransactionHistoryItem:
    amount = transaction.amount or Decimal("0")
    if (transaction.type or "").upper() == "DEBIT":
        amount = -amount
    description = "Ledger transaction"
    if transaction.external_ref and transaction.type == "CREDIT":
        description = f"Top-up via {transaction.external_ref}"
    elif transaction.endorsement_id:
        description = f"Endorsement {transaction.endorsement_id}"

    return LedgerTransactionHistoryItem(
        id=transaction.id,
        employer_id=transaction.employer_id,
        date=transaction.created_at,
        type=transaction.type,
        amount=amount,
        status=transaction.status,
        description=description,
        external_reference=transaction.external_ref,
        endorsement_id=transaction.endorsement_id,
    )


async def _count_employers(session: AsyncSession, employer_id: str | None) -> int:
    query = select(func.count()).select_from(Employer)
    if employer_id:
        query = query.where(Employer.id == employer_id)
    result = await session.execute(query)
    return result.scalar() or 0


@router.get(
    "/balance",
    response_model=PaginatedResponse[LedgerBalanceResponse],
    summary="List ledger balances",
    description="Returns ledger balances for employers. Supports optional pagination and employer filtering.",
)
async def list_ledger_balances(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    employer_id: str | None = Query(
        None, description="Optional employer ID to filter the balance result"
    ),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["ledger:read"]),
) -> PaginatedResponse[LedgerBalanceResponse]:
    resolved_employer = _resolve_employer_scope(employer_id, current_user)

    locked_subquery = (
        select(
            LedgerTransaction.employer_id.label("employer_id"),
            func.coalesce(func.sum(LedgerTransaction.amount), 0).label("locked_funds"),
        )
        .where(
            LedgerTransaction.type == "DEBIT",
            LedgerTransaction.status.in_(LOCKED_DEBIT_STATUSES),
        )
        .group_by(LedgerTransaction.employer_id)
        .subquery()
    )

    balance_query = (
        select(Employer, locked_subquery.c.locked_funds)
        .outerjoin(locked_subquery, Employer.id == locked_subquery.c.employer_id)
        .order_by(Employer.name.asc())
    )

    if resolved_employer:
        balance_query = balance_query.where(Employer.id == resolved_employer)

    total = await _count_employers(session, resolved_employer)
    result = await session.execute(balance_query.offset(offset).limit(limit))
    rows = result.all()

    balance_data = [
        _build_balance_item(employer, locked_amount)
        for employer, locked_amount in rows
    ]

    paginated = PaginatedResponse.create(
        data=balance_data,
        total=total,
        limit=limit,
        offset=offset,
        object_type="ledger.balance.list",
    )

    base_url = str(request.url).split("?")[0]
    link_header = build_link_header(base_url, total, limit, offset)
    if link_header:
        response.headers["Link"] = link_header
    response.headers["X-Total-Count"] = str(total)

    return paginated


@router.post(
    "/topup",
    response_model=LedgerTopUpResponse,
    status_code=201,
    summary="Top-up an employer ledger",
    description="Credits funds to an employer's endorsement account.",
)
async def top_up_ledger(
    request: LedgerTopUpRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["ledger:write"]),
) -> LedgerTopUpResponse:
    caller_employer = current_user.get("employer_id")
    if caller_employer and caller_employer != request.employer_id:
        raise ForbiddenError("Access denied. You can only top-up your own employer.")

    repository = EmployerRepository(session)
    employer = await repository.get_by_id_for_update(request.employer_id)
    if not employer:
        raise ResourceNotFoundError("Employer", request.employer_id)

    new_balance = (employer.ea_balance or Decimal("0")) + request.amount
    employer.ea_balance = new_balance

    transaction = LedgerTransaction(
        employer_id=employer.id,
        endorsement_id=None,
        type="CREDIT",
        amount=request.amount,
        status="CLEARED",
        external_ref=request.transaction_reference,
    )
    session.add(transaction)
    await session.flush()
    await session.commit()

    LEDGER_BALANCE.labels(employer_id=employer.id).set(float(new_balance))

    return LedgerTopUpResponse(
        transaction_id=transaction.id,
        employer_id=employer.id,
        transaction_reference=request.transaction_reference,
        amount=request.amount,
        currency=request.currency,
        payment_method=request.payment_method,
        timestamp=request.timestamp,
        status=transaction.status,
        new_balance=new_balance,
    )


@router.get(
    "/history",
    response_model=PaginatedResponse[LedgerTransactionHistoryItem],
    summary="Ledger transaction history",
    description="Returns the audit trail of ledger credits and debits.",
)
async def ledger_history(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    employer_id: str | None = Query(
        None, description="Optional employer ID to scope the history"
    ),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["ledger:read"]),
) -> PaginatedResponse[LedgerTransactionHistoryItem]:
    resolved_employer = _resolve_employer_scope(employer_id, current_user)

    history_query = select(LedgerTransaction).order_by(LedgerTransaction.created_at.desc())
    if resolved_employer:
        history_query = history_query.where(LedgerTransaction.employer_id == resolved_employer)

    total_query = select(func.count()).select_from(LedgerTransaction)
    if resolved_employer:
        total_query = total_query.where(LedgerTransaction.employer_id == resolved_employer)

    result = await session.execute(history_query.offset(offset).limit(limit))
    transactions = result.scalars().all()

    total_result = await session.execute(total_query)
    total = total_result.scalar() or 0

    history_items = [_build_history_item(txn) for txn in transactions]

    paginated = PaginatedResponse.create(
        data=history_items,
        total=total,
        limit=limit,
        offset=offset,
        object_type="ledger.transactions",
    )

    base_url = str(request.url).split("?")[0]
    link_header = build_link_header(base_url, total, limit, offset)
    if link_header:
        response.headers["Link"] = link_header
    response.headers["X-Total-Count"] = str(total)

    return paginated
