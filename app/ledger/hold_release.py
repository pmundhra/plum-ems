"""Hold-release helpers for the ledger domain."""

from __future__ import annotations

from typing import Any

from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.postgres import get_postgres_adapter
from app.core.metrics import KAFKA_MESSAGES_PRODUCED
from app.core.settings import settings
from app.endorsement_request.repository import EndorsementRequestRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HoldReleaseService:
    """Wake parked endorsements when the ledger balance recovers."""

    def __init__(self) -> None:
        self._producer = get_kafka_producer()
        self._postgres = get_postgres_adapter()

    async def release_on_hold_requests(self, event_payload: dict[str, Any]) -> None:
        employer_id = event_payload.get("employer_id")
        if not employer_id:
            logger.error("hold_release_missing_employer_id", payload=event_payload)
            return

        async with self._postgres.get_session() as session:
            repository = EndorsementRequestRepository(session)
            on_hold_requests = await repository.get_on_hold_by_employer_id(employer_id)
            if not on_hold_requests:
                logger.info("hold_release_no_requests", employer_id=employer_id)
                return

            released = 0
            for request in on_hold_requests:
                await repository.update(
                    request.id,
                    employer_id=employer_id,
                    status="VALIDATED",
                )
                self._dispatch_ledger_retry(request)
                released += 1

            logger.info(
                "hold_release_dispatched",
                employer_id=employer_id,
                released=released,
                change_amount=event_payload.get("change_amount"),
                new_balance=event_payload.get("new_balance"),
            )

    def _dispatch_ledger_retry(self, request: Any) -> None:
        payload = {
            "endorsement_id": request.id,
            "employer_id": request.employer_id,
            "request_type": request.type,
            "effective_date": request.effective_date.isoformat(),
            "payload": request.payload,
            "trace_id": request.trace_id,
            "retry_count": request.retry_count,
        }
        try:
            self._producer.produce(
                topic=settings.KAFKA_TOPIC_LEDGER_CHECK_FUNDS,
                value=payload,
                key=request.id,
            )
            KAFKA_MESSAGES_PRODUCED.labels(
                topic=settings.KAFKA_TOPIC_LEDGER_CHECK_FUNDS
            ).inc()
        except Exception as exc:
            logger.exception(
                "hold_release_ledger_publish_failed",
                endorsement_id=request.id,
                employer_id=request.employer_id,
                error=str(exc),
            )
