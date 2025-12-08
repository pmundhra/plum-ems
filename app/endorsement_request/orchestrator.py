"""Endorsement orchestrator workflow helpers."""

from __future__ import annotations

from typing import Any

from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.postgres import get_postgres_adapter
from app.core.metrics import ENDORSEMENTS_PROCESSED_TOTAL, KAFKA_MESSAGES_PRODUCED
from app.core.settings import settings
from app.endorsement_request.repository import EndorsementRequestRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EndorsementOrchestratorService:
    """Orchestrates lifecycle transitions across Kafka events."""

    VALIDATED_STATUS = "VALIDATED"
    FUNDS_LOCKED_STATUS = "FUNDS_LOCKED"
    COMPLETED_STATUS = "COMPLETED"

    def __init__(self) -> None:
        self._producer = get_kafka_producer()
        self._postgres = get_postgres_adapter()

    async def handle_prioritized_event(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        if not endorsement_id or not employer_id:
            logger.warning(
                "orchestrator_skipping_prioritized",
                payload=kafka_payload,
            )
            return

        await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.VALIDATED_STATUS,
        )

        ledger_payload = self._build_ledger_payload(kafka_payload)
        self._publish_event(
            topic=settings.KAFKA_TOPIC_LEDGER_CHECK_FUNDS,
            value=ledger_payload,
            key=endorsement_id,
        )

    async def handle_funds_locked_event(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        if not endorsement_id or not employer_id:
            logger.warning(
                "orchestrator_skipping_funds_locked",
                payload=kafka_payload,
            )
            return

        await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.FUNDS_LOCKED_STATUS,
        )

        insurer_payload = self._build_insurer_request_payload(kafka_payload)
        self._publish_event(
            topic=settings.KAFKA_TOPIC_INSURER_REQUEST,
            value=insurer_payload,
            key=endorsement_id,
        )

    async def handle_insurer_success_event(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        if not endorsement_id or not employer_id:
            logger.warning(
                "orchestrator_skipping_insurer_success",
                payload=kafka_payload,
            )
            return

        await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.COMPLETED_STATUS,
        )

        completion_payload = self._build_completion_payload(kafka_payload)
        self._publish_event(
            topic=settings.KAFKA_TOPIC_ENDORSEMENT_COMPLETED,
            value=completion_payload,
            key=endorsement_id,
        )

    async def _update_request_status(self, endorsement_id: str, employer_id: str, status: str) -> None:
        try:
            async with self._postgres.get_session() as session:
                repo = EndorsementRequestRepository(session)
                updated = await repo.update(
                    endorsement_id,
                    employer_id=employer_id,
                    status=status,
                )

            if updated:
                ENDORSEMENTS_PROCESSED_TOTAL.labels(status=status, type=updated.type).inc()
                logger.info(
                    "orchestrator_status_updated",
                    endorsement_id=endorsement_id,
                    employer_id=employer_id,
                    status=status,
                )
            else:
                logger.warning(
                    "orchestrator_request_missing",
                    endorsement_id=endorsement_id,
                    employer_id=employer_id,
                )
        except Exception as exc:
            logger.error(
                "orchestrator_status_update_failed",
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                error=str(exc),
            )

    def _build_ledger_payload(self, kafka_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "endorsement_id": kafka_payload.get("endorsement_id"),
            "employer_id": kafka_payload.get("employer_id"),
            "request_type": kafka_payload.get("type"),
            "effective_date": kafka_payload.get("effective_date"),
            "payload": kafka_payload.get("payload"),
            "trace_id": kafka_payload.get("trace_id"),
        }

    def _build_insurer_request_payload(self, kafka_payload: dict[str, Any]) -> dict[str, Any]:
        insurer_payload = {
            "endorsement_id": kafka_payload.get("endorsement_id"),
            "employer_id": kafka_payload.get("employer_id"),
            "request_type": kafka_payload.get("type"),
            "trace_id": kafka_payload.get("trace_id"),
            "payload": kafka_payload.get("payload"),
            "ledger_context": {
                "locked_amount": kafka_payload.get("locked_amount"),
                "reservation_id": kafka_payload.get("reservation_id"),
            },
        }
        return insurer_payload

    def _build_completion_payload(self, kafka_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "endorsement_id": kafka_payload.get("endorsement_id"),
            "employer_id": kafka_payload.get("employer_id"),
            "trace_id": kafka_payload.get("trace_id"),
            "insurer_response": kafka_payload.get("insurer_response") or kafka_payload.get("response"),
        }

    def _publish_event(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        try:
            headers = self._build_headers(value)
            self._producer.produce(
                topic=topic,
                value=value,
                key=key,
                headers=headers,
            )
            KAFKA_MESSAGES_PRODUCED.labels(topic=topic).inc()
        except Exception as exc:
            logger.error(
                "orchestrator_publish_failed",
                topic=topic,
                endorsement_id=value.get("endorsement_id"),
                error=str(exc),
            )

    def _build_headers(self, value: dict[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {"source": "orchestrator"}
        trace_id = value.get("trace_id")
        employer_id = value.get("employer_id")
        if trace_id:
            headers["trace_id"] = str(trace_id)
        if employer_id:
            headers["employer_id"] = str(employer_id)
        return headers
