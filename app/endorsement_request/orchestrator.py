"""Endorsement orchestrator workflow helpers."""

from __future__ import annotations

from typing import Any

from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.postgres import get_postgres_adapter
from app.core.metrics import ENDORSEMENTS_PROCESSED_TOTAL, KAFKA_MESSAGES_PRODUCED
from app.core.settings import settings
from app.endorsement_request.model import EndorsementRequest
from app.endorsement_request.repository import EndorsementRequestRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EndorsementOrchestratorService:
    """Orchestrates lifecycle transitions across Kafka events."""

    STATUS_RECEIVED = "RECEIVED"
    STATUS_VALIDATED = "VALIDATED"
    STATUS_FUNDS_LOCKED = "FUNDS_LOCKED"
    STATUS_SENT = "SENT"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_FAILED = "FAILED"
    STATUS_ON_HOLD = "ON_HOLD"

    LEDGER_STATUS_LOCKED = "LOCKED"
    LEDGER_STATUS_ON_HOLD = "ON_HOLD"
    INSURER_STATUS_SUCCESS = "SUCCESS"

    def __init__(self) -> None:
        self._producer = get_kafka_producer()
        self._postgres = get_postgres_adapter()
        self._retry_topic = settings.KAFKA_TOPIC_INSURER_REQUEST_RETRY
        self._dlq_topic = settings.KAFKA_TOPIC_INSURER_REQUEST_DLQ
        self._max_insurer_retries = max(settings.INSURER_MAX_RETRIES, 1)
        self._backoff_base = max(settings.ENDORSEMENT_RETRY_BACKOFF_BASE, 2)

    async def handle_prioritized_event(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        if not endorsement_id or not employer_id:
            logger.warning(
                "orchestrator_skipping_prioritized",
                payload=kafka_payload,
            )
            return

        updated = await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.STATUS_VALIDATED,
        )
        if not updated:
            return

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

        ledger_status = (kafka_payload.get("status") or "").upper()
        if ledger_status == self.LEDGER_STATUS_LOCKED:
            endorsement = await self._update_request_status(
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                status=self.STATUS_FUNDS_LOCKED,
            )
            if not endorsement:
                return
            await self._dispatch_insurer_request(kafka_payload, endorsement)
        elif ledger_status == self.LEDGER_STATUS_ON_HOLD:
            await self._update_request_status(
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                status=self.STATUS_ON_HOLD,
            )
        else:
            await self._update_request_status(
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                status=self.STATUS_FAILED,
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

        status = (kafka_payload.get("status") or self.INSURER_STATUS_SUCCESS).upper()
        if status == self.INSURER_STATUS_SUCCESS:
            await self._finalize_success(endorsement_id, employer_id, kafka_payload)
            return

        error_type = (kafka_payload.get("error_type") or "TECHNICAL").upper()
        await self._handle_insurer_failure(
            kafka_payload=kafka_payload,
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            error_type=error_type,
        )

    async def _dispatch_insurer_request(
        self, kafka_payload: dict[str, Any], endorsement: EndorsementRequest
    ) -> None:
        await self._update_request_status(
            endorsement_id=endorsement.id,
            employer_id=endorsement.employer_id,
            status=self.STATUS_SENT,
        )

        insurer_payload = self._build_insurer_request_payload(
            kafka_payload=kafka_payload,
            fallback_payload=endorsement.payload,
        )
        insurer_payload["retry_count"] = endorsement.retry_count or 0

        self._publish_event(
            topic=settings.KAFKA_TOPIC_INSURER_REQUEST,
            value=insurer_payload,
            key=endorsement.id,
        )

    async def _finalize_success(
        self, endorsement_id: str, employer_id: str, kafka_payload: dict[str, Any]
    ) -> None:
        confirmed = await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.STATUS_CONFIRMED,
        )
        if not confirmed:
            return

        completion_payload = self._build_completion_payload(kafka_payload, confirmed)
        self._publish_event(
            topic=settings.KAFKA_TOPIC_ENDORSEMENT_COMPLETED,
            value=completion_payload,
            key=endorsement_id,
        )

        await self._update_request_status(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            status=self.STATUS_ACTIVE,
        )

    async def _handle_insurer_failure(
        self,
        kafka_payload: dict[str, Any],
        endorsement_id: str,
        employer_id: str,
        error_type: str,
    ) -> None:
        endorsement = await self._get_endorsement(endorsement_id, employer_id)
        if not endorsement:
            return

        error_details = self._extract_error_details(kafka_payload)
        if error_type == "BUSINESS":
            await self._mark_failed_business(endorsement, error_details)
            return

        await self._schedule_insurer_retry(kafka_payload, endorsement, error_details)

    async def _schedule_insurer_retry(
        self,
        kafka_payload: dict[str, Any],
        endorsement: EndorsementRequest,
        error_details: dict[str, Any],
    ) -> None:
        next_retry = endorsement.retry_count + 1
        if next_retry > self._max_insurer_retries:
            await self._update_request_status(
                endorsement_id=endorsement.id,
                employer_id=endorsement.employer_id,
                status=self.STATUS_FAILED,
                retry_count=next_retry,
            )
            dlq_payload = self._build_dlq_payload(
                endorsement, error_details, kafka_payload
            )
            self._publish_event(
                topic=self._dlq_topic,
                value=dlq_payload,
                key=endorsement.id,
            )
            logger.warning(
                "orchestrator_retry_limit_exceeded",
                endorsement_id=endorsement.id,
                employer_id=endorsement.employer_id,
                retry_count=next_retry,
            )
            return

        retry_payload = self._build_insurer_request_payload(
            kafka_payload=kafka_payload,
            fallback_payload=endorsement.payload,
        )
        retry_payload["retry_count"] = next_retry
        retry_payload["retry_delay_seconds"] = self._calculate_retry_delay_seconds(
            next_retry
        )
        if error_details:
            retry_payload["last_error"] = error_details

        self._publish_event(
            topic=self._retry_topic,
            value=retry_payload,
            key=endorsement.id,
            extra_headers={"retry_after_seconds": retry_payload["retry_delay_seconds"]},
        )

        await self._update_request_status(
            endorsement_id=endorsement.id,
            employer_id=endorsement.employer_id,
            status=self.STATUS_SENT,
            retry_count=next_retry,
        )

        logger.warning(
            "orchestrator_insurer_retry_scheduled",
            endorsement_id=endorsement.id,
            employer_id=endorsement.employer_id,
            next_retry=next_retry,
            delay_seconds=retry_payload["retry_delay_seconds"],
        )

    async def _mark_failed_business(
        self, endorsement: EndorsementRequest, error_details: dict[str, Any]
    ) -> None:
        await self._update_request_status(
            endorsement_id=endorsement.id,
            employer_id=endorsement.employer_id,
            status=self.STATUS_FAILED,
            retry_count=endorsement.retry_count,
        )
        dlq_payload = self._build_dlq_payload(endorsement, error_details)
        self._publish_event(
            topic=self._dlq_topic,
            value=dlq_payload,
            key=endorsement.id,
        )
        logger.warning(
            "orchestrator_insurer_business_failure",
            endorsement_id=endorsement.id,
            employer_id=endorsement.employer_id,
            error=error_details,
        )

    async def _get_endorsement(
        self, endorsement_id: str, employer_id: str
    ) -> EndorsementRequest | None:
        async with self._postgres.get_session() as session:
            repo = EndorsementRequestRepository(session)
            return await repo.get_by_id(endorsement_id, employer_id=employer_id)

    async def _update_request_status(
        self,
        endorsement_id: str,
        employer_id: str,
        status: str,
        retry_count: int | None = None,
    ) -> EndorsementRequest | None:
        try:
            async with self._postgres.get_session() as session:
                repo = EndorsementRequestRepository(session)
                updated = await repo.update(
                    endorsement_id,
                    employer_id=employer_id,
                    status=status,
                    **({"retry_count": retry_count} if retry_count is not None else {}),
                )

            if updated:
                ENDORSEMENTS_PROCESSED_TOTAL.labels(
                    status=status,
                    type=updated.type,
                ).inc()
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

            return updated
        except Exception as exc:
            logger.error(
                "orchestrator_status_update_failed",
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                error=str(exc),
            )
            return None

    def _build_ledger_payload(self, kafka_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "endorsement_id": kafka_payload.get("endorsement_id"),
            "employer_id": kafka_payload.get("employer_id"),
            "request_type": kafka_payload.get("type"),
            "effective_date": kafka_payload.get("effective_date"),
            "payload": kafka_payload.get("payload"),
            "trace_id": kafka_payload.get("trace_id"),
        }

    def _build_insurer_request_payload(
        self,
        kafka_payload: dict[str, Any],
        fallback_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ledger_context = {
            key: kafka_payload.get(key)
            for key in ("locked_amount", "reservation_id", "new_balance")
            if kafka_payload.get(key) is not None
        }

        payload = kafka_payload.get("payload") or fallback_payload or {}
        insurer_id = (
            payload.get("insurer_id")
            or (payload.get("coverage") or {}).get("insurer_id")
            or kafka_payload.get("insurer_id")
        )
        insurer_payload: dict[str, Any] = {
            "endorsement_id": kafka_payload.get("endorsement_id"),
            "employer_id": kafka_payload.get("employer_id"),
            "request_type": kafka_payload.get("type"),
            "trace_id": kafka_payload.get("trace_id"),
            "payload": payload,
            "ledger_context": ledger_context,
        }
        if insurer_id:
            insurer_payload["insurer_id"] = insurer_id
        return insurer_payload

    def _build_completion_payload(
        self, kafka_payload: dict[str, Any], endorsement: EndorsementRequest
    ) -> dict[str, Any]:
        return {
            "endorsement_id": endorsement.id,
            "employer_id": endorsement.employer_id,
            "trace_id": kafka_payload.get("trace_id") or endorsement.trace_id,
            "retry_count": endorsement.retry_count,
            "status": self.STATUS_ACTIVE,
            "insurer_response": kafka_payload.get("insurer_response")
            or kafka_payload.get("response"),
        }

    def _build_dlq_payload(
        self,
        endorsement: EndorsementRequest,
        error_details: dict[str, Any],
        kafka_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "endorsement_id": endorsement.id,
            "employer_id": endorsement.employer_id,
            "type": endorsement.type,
            "payload": endorsement.payload,
            "trace_id": endorsement.trace_id,
            "retry_count": endorsement.retry_count,
            "status": self.STATUS_FAILED,
            "error": error_details,
        }

        if kafka_payload:
            payload["insurer_status"] = kafka_payload.get("status")
            payload["insurer_response"] = kafka_payload.get("insurer_response") or kafka_payload.get("response")

        return payload

    def _extract_error_details(self, kafka_payload: dict[str, Any]) -> dict[str, Any]:
        error = kafka_payload.get("error")
        if isinstance(error, dict) and error:
            return error

        return {
            "message": kafka_payload.get("message")
            or kafka_payload.get("error_message")
            or kafka_payload.get("status"),
            "code": kafka_payload.get("error_code"),
        }

    def _calculate_retry_delay_seconds(self, retry_count: int) -> int:
        delay = self._backoff_base**retry_count
        return int(delay * 60)

    def _publish_event(
        self,
        topic: str,
        value: dict[str, Any],
        key: str | None = None,
        extra_headers: dict[str, Any] | None = None,
    ) -> None:
        try:
            headers = self._build_headers(value)
            if extra_headers:
                headers.update({k: str(v) for k, v in extra_headers.items()})
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
