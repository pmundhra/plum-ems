"""Ledger service for locking funds before insurer execution."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.postgres import get_postgres_adapter
from app.core.metrics import KAFKA_MESSAGES_PRODUCED, LEDGER_TRANSACTIONS_TOTAL
from app.core.settings import settings
from app.employer.repository import EmployerRepository
from app.ledger.pricing import LedgerPricingClient
from app.ledger_transaction.model import LedgerTransaction
from app.utils.logger import get_logger
from app.ledger.events import publish_balance_increase

logger = get_logger(__name__)


class LedgerService:
    """Handles ledger.check_funds events and emits funds.locked events."""

    def __init__(self) -> None:
        self._producer = get_kafka_producer()
        self._postgres = get_postgres_adapter()
        self._pricing_client = LedgerPricingClient()

    async def process_check_funds(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        request_type = kafka_payload.get("request_type", "ADDITION")
        trace_id = kafka_payload.get("trace_id")

        if not endorsement_id or not employer_id:
            logger.warning(
                "ledger_missing_ids",
                payload=kafka_payload,
            )
            return

        amount = await self._resolve_amount(kafka_payload, request_type)
        amount = max(Decimal(0), amount)
        is_credit = request_type.upper() == "DELETION"

        async with self._postgres.get_session() as session:
            employer_repo = EmployerRepository(session)
            employer = await employer_repo.get_by_id_for_update(employer_id)

            if not employer:
                logger.error(
                    "ledger_employer_not_found",
                    employer_id=employer_id,
                    endorsement_id=endorsement_id,
                )
                await self._emit_funds_locked_event(
                    endorsement_id,
                    employer_id,
                    amount,
                    "FAILED",
                    trace_id,
                    message="Employer not found",
                )
                return

            current_balance = Decimal(employer.ea_balance or 0)
            new_balance = current_balance + amount if is_credit else current_balance - amount

            if not is_credit and current_balance < amount:
                logger.warning(
                    "ledger_insufficient_funds",
                    employer_id=employer_id,
                    endorsement_id=endorsement_id,
                    requested_amount=str(amount),
                    available_balance=str(current_balance),
                )
                txn = LedgerTransaction(
                    employer_id=employer.id,
                    endorsement_id=endorsement_id,
                    type="DEBIT",
                    amount=amount,
                    status="ON_HOLD_FUNDS",
                )
                session.add(txn)
                await session.flush()
                await self._emit_funds_locked_event(
                    endorsement_id,
                    employer_id,
                    amount,
                    "ON_HOLD",
                    trace_id,
                    message="Insufficient funds",
                )
                LEDGER_TRANSACTIONS_TOTAL.labels(type=txn.type, status=txn.status).inc()
                return

            txn = LedgerTransaction(
                employer_id=employer.id,
                endorsement_id=endorsement_id,
                type="CREDIT" if is_credit else "DEBIT",
                amount=amount,
                status="LOCKED",
            )
            session.add(txn)

            employer.ea_balance = new_balance
            await session.flush()

        LEDGER_TRANSACTIONS_TOTAL.labels(type=txn.type, status=txn.status).inc()
        if is_credit and amount > Decimal("0"):
            publish_balance_increase(
                employer.id,
                amount,
                new_balance,
                source="ledger_credit",
            )
        await self._emit_funds_locked_event(
            endorsement_id,
            employer_id,
            amount,
            "LOCKED",
            trace_id,
            new_balance=new_balance,
            request_type=request_type,
        )

    async def _emit_funds_locked_event(
        self,
        endorsement_id: str,
        employer_id: str,
        locked_amount: Decimal,
        status: str,
        trace_id: str | None,
        message: str | None = None,
        new_balance: Decimal | None = None,
        request_type: str | None = None,
    ) -> None:
        reservation_id = uuid4().hex
        payload: dict[str, Any] = {
            "endorsement_id": endorsement_id,
            "employer_id": employer_id,
            "locked_amount": str(locked_amount),
            "reservation_id": reservation_id,
            "status": status,
        }
        if trace_id:
            payload["trace_id"] = trace_id
        if new_balance is not None:
            payload["new_balance"] = str(new_balance)
        if request_type:
            payload["request_type"] = request_type
        if message:
            payload["message"] = message

        try:
            headers = {"source": "ledger"}
            if trace_id:
                headers["trace_id"] = str(trace_id)
            headers["employer_id"] = employer_id

            self._producer.produce(
                topic=settings.KAFKA_TOPIC_LEDGER_FUNDS_LOCKED,
                value=payload,
                key=endorsement_id,
                headers=headers,
            )
            KAFKA_MESSAGES_PRODUCED.labels(topic=settings.KAFKA_TOPIC_LEDGER_FUNDS_LOCKED).inc()
        except Exception as exc:
            logger.error(
                "ledger_emit_failed",
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                error=str(exc),
            )

    async def _resolve_amount(
        self,
        payload: dict[str, Any],
        request_type: str,
    ) -> Decimal:
        """
        Determine the amount to lock by checking request payload and pricing stub.
        """
        amount = self._extract_amount(payload)
        if amount > Decimal("0"):
            return amount

        context = payload.get("payload", {})
        return await self._pricing_client.get_endorsement_price(request_type, context)

    def _extract_amount(self, payload: dict[str, Any]) -> Decimal:
        amount = payload.get("amount")
        if amount is None and payload.get("payload"):
            amount = payload["payload"].get("amount")
            if amount is None:
                coverage = payload["payload"].get("coverage")
                if coverage:
                    amount = coverage.get("amount")
        try:
            return Decimal(str(amount)) if amount is not None else Decimal("0")
        except (TypeError, InvalidOperation):
            return Decimal("0")
