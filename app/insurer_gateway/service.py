"""Insurer gateway helpers: deliver requests, log interactions, emit events."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.audit_log.model import (
    AuditLogDocument,
    AuditLogError,
    AuditLogRequest,
    AuditLogResponse,
)
from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.mongo import get_mongo_adapter
from app.core.metrics import (
    KAFKA_MESSAGES_PRODUCED,
    INSURER_REQUEST_DURATION,
    INSURER_REQUEST_FAILURES,
    INSURER_REQUESTS_TOTAL,
)
from app.core.settings import settings
from app.core.settings.base import InsurerGatewayConfigEntry
from app.insurer_gateway.strategies import (
    GatewayRequest,
    GatewayStrategy,
    HttpGatewayStrategy,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

SENSITIVE_KEYS = {"ssn", "dob"}
DEFAULT_PROTOCOL = "REST_API"
AUDIT_COLLECTION = "audit_logs"


class InsurerGatewayService:
    """Executes insurer requests, records audit logs, and publishes Kafka acknowledgements."""

    def __init__(self) -> None:
        self._producer = get_kafka_producer()
        self._mongo = get_mongo_adapter()
        self._strategies: dict[str, GatewayStrategy] = {
            HttpGatewayStrategy.protocol_name: HttpGatewayStrategy(),
        }
        self._default_protocol = HttpGatewayStrategy.protocol_name
        self._default_strategy = self._strategies[self._default_protocol]

    async def process_insurer_request(self, kafka_payload: dict[str, Any]) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")

        if not endorsement_id or not employer_id:
            logger.error(
                "insurer_gateway_missing_ids",
                payload=kafka_payload,
            )
            return

        trace_id = kafka_payload.get("trace_id")
        insurer_id = self._resolve_insurer_id(kafka_payload)
        if not insurer_id:
            await self._handle_missing_insurer_id(kafka_payload, endorsement_id, employer_id, trace_id)
            return

        config = settings.INSURER_GATEWAY_CONFIG.get(insurer_id)
        if not config:
            await self._handle_missing_config(kafka_payload, endorsement_id, employer_id, trace_id, insurer_id)
            return

        logger.info(f"Processing insurer request for {insurer_id} with config {config}")
        logger.info(f"Request body: {kafka_payload.get('payload')}")
        
        request_body = kafka_payload.get("payload") or {}
        request_headers = self._build_request_headers(config, kafka_payload, insurer_id, endorsement_id)
        request_url = config.url.format(insurer_id=insurer_id)
        timeout_seconds = config.timeout_seconds or settings.INSURER_REQUEST_TIMEOUT_SECONDS
        protocol = config.protocol or DEFAULT_PROTOCOL
        strategy = self._get_strategy(protocol)

        request_snapshot = self._build_request_snapshot(
            request_url, config.method, request_headers, request_body
        )

        gateway_request = GatewayRequest(
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            trace_id=trace_id,
            kafka_payload=kafka_payload,
            retry_count=kafka_payload.get("retry_count", 0),
            request_body=request_body,
            request_headers=request_headers,
            request_url=request_url,
            timeout_seconds=timeout_seconds,
            config=config,
        )

        start_time = time.perf_counter()
        result = await strategy.execute(gateway_request)
        duration = time.perf_counter() - start_time
        response_snapshot = self._build_response_snapshot(result.response)

        await self._record_metrics(insurer_id, protocol, result.status, duration, result.error_type)
        await self._record_audit_entry(
            endorsement_id=endorsement_id,
            trace_id=trace_id,
            insurer_id=insurer_id,
            protocol=protocol,
            status=result.status,
            latency_ms=duration * 1000,
            request=request_snapshot,
            response=response_snapshot,
            error=AuditLogError(**result.error_details) if result.error_details else None,
        )

        await self._publish_insurer_event(
            kafka_payload=kafka_payload,
            insurer_id=insurer_id,
            status=result.status,
            response=result.response,
            error_details=result.error_details,
            error_type=result.error_type,
        )

    async def _handle_missing_insurer_id(
        self,
        kafka_payload: dict[str, Any],
        endorsement_id: str,
        employer_id: str,
        trace_id: str | None,
    ) -> None:
        error_details = {
            "code": "INSURER_ID_MISSING",
            "message": "Insurer identifier could not be resolved from payload",
        }
        await self._record_metrics("unknown", DEFAULT_PROTOCOL, "FAILURE", 0.0, "TECHNICAL")
        await self._record_audit_entry(
            endorsement_id=endorsement_id,
            trace_id=trace_id,
            insurer_id="unknown",
            protocol=DEFAULT_PROTOCOL,
            status="FAILURE",
            latency_ms=0.0,
            request=self._build_request_snapshot("", "POST", {}, {}),
            response=None,
            error=AuditLogError(**error_details),
        )
        await self._publish_insurer_event(
            kafka_payload=kafka_payload,
            insurer_id="unknown",
            status="FAILURE",
            response=None,
            error_details=error_details,
            error_type="TECHNICAL",
        )

    async def _handle_missing_config(
        self,
        kafka_payload: dict[str, Any],
        endorsement_id: str,
        employer_id: str,
        trace_id: str | None,
        insurer_id: str,
    ) -> None:
        error_details = {
            "code": "GATEWAY_CONFIG_MISSING",
            "message": f"No gateway configuration defined for insurer '{insurer_id}'",
        }
        await self._record_metrics(insurer_id, DEFAULT_PROTOCOL, "FAILURE", 0.0, "TECHNICAL")
        await self._record_audit_entry(
            endorsement_id=endorsement_id,
            trace_id=trace_id,
            insurer_id=insurer_id,
            protocol=DEFAULT_PROTOCOL,
            status="FAILURE",
            latency_ms=0.0,
            request=self._build_request_snapshot("", "POST", {}, {}),
            response=None,
            error=AuditLogError(**error_details),
        )
        await self._publish_insurer_event(
            kafka_payload=kafka_payload,
            insurer_id=insurer_id,
            status="FAILURE",
            response=None,
            error_details=error_details,
            error_type="TECHNICAL",
        )

    async def _record_metrics(
        self,
        insurer_id: str,
        protocol: str,
        status: str,
        duration: float,
        error_type: str,
    ) -> None:
        INSURER_REQUESTS_TOTAL.labels(
            insurer_id=insurer_id,
            protocol=protocol,
            status=status,
        ).inc()
        INSURER_REQUEST_DURATION.labels(insurer_id=insurer_id, protocol=protocol).observe(duration)
        if status != "SUCCESS" and error_type:
            INSURER_REQUEST_FAILURES.labels(
                insurer_id=insurer_id,
                protocol=protocol,
                error_type=error_type,
            ).inc()

    def _get_strategy(self, protocol: str) -> GatewayStrategy:
        return self._strategies.get(protocol, self._default_strategy)

    async def _record_audit_entry(
        self,
        endorsement_id: str,
        trace_id: str | None,
        insurer_id: str,
        protocol: str,
        status: str,
        latency_ms: float,
        request: AuditLogRequest,
        response: AuditLogResponse | None,
        error: AuditLogError | None,
    ) -> None:
        try:
            document = AuditLogDocument(
                endorsement_id=endorsement_id,
                trace_id=trace_id,
                insurer_id=insurer_id,
                interaction_type=protocol,
                latency_ms=latency_ms,
                status=status,
                request=request,
                response=response,
                error=error,
            )
            await self._mongo.insert_one(settings.MONGO_DB, AUDIT_COLLECTION, document.model_dump())
        except Exception as exc:
            logger.error(
                "insurer_gateway_audit_failed",
                endorsement_id=endorsement_id,
                insurer_id=insurer_id,
                error=str(exc),
            )

    async def _publish_insurer_event(
        self,
        kafka_payload: dict[str, Any],
        insurer_id: str,
        status: str,
        response: httpx.Response | None,
        error_details: dict[str, Any] | None,
        error_type: str,
    ) -> None:
        endorsement_id = kafka_payload.get("endorsement_id")
        employer_id = kafka_payload.get("employer_id")
        trace_id = kafka_payload.get("trace_id")
        event_payload: dict[str, Any] = {
            "endorsement_id": endorsement_id,
            "employer_id": employer_id,
            "insurer_id": insurer_id,
            "trace_id": trace_id,
            "status": status,
            "retry_count": kafka_payload.get("retry_count", 0),
            "insurer_response": self._extract_response_payload(response),
        }
        if error_details:
            event_payload["error"] = error_details
            event_payload["error_type"] = error_type

        try:
            headers = {
                "source": "insurer_gateway",
            }
            if trace_id:
                headers["trace_id"] = str(trace_id)
            if employer_id:
                headers["employer_id"] = str(employer_id)

            self._producer.produce(
                topic=settings.KAFKA_TOPIC_INSURER_SUCCESS,
                value=event_payload,
                key=str(endorsement_id),
                headers=headers,
            )
            KAFKA_MESSAGES_PRODUCED.labels(topic=settings.KAFKA_TOPIC_INSURER_SUCCESS).inc()
        except Exception as exc:
            logger.error(
                "insurer_gateway_event_publish_failed",
                endorsement_id=endorsement_id,
                employer_id=employer_id,
                error=str(exc),
                topic=settings.KAFKA_TOPIC_INSURER_SUCCESS,
            )

    def _resolve_insurer_id(self, kafka_payload: dict[str, Any]) -> str | None:
        payload = kafka_payload.get("payload") or {}
        coverage = payload.get("coverage") or {}
        insurer_id = coverage.get("insurer_id") or payload.get("insurer_id") or kafka_payload.get("insurer_id")
        if isinstance(insurer_id, str):
            return insurer_id
        return None

    def _build_request_headers(
        self,
        config: InsurerGatewayConfigEntry,
        kafka_payload: dict[str, Any],
        insurer_id: str,
        endorsement_id: str,
    ) -> dict[str, str]:
        headers = {k: str(v) for k, v in (config.headers or {}).items()}
        trace_id = kafka_payload.get("trace_id")
        employer_id = kafka_payload.get("employer_id")
        headers.setdefault("Content-Type", "application/json")
        if trace_id:
            headers.setdefault("trace_id", str(trace_id))
        if employer_id:
            headers.setdefault("employer_id", str(employer_id))
        retry_count = kafka_payload.get("retry_count", 0)
        headers.setdefault(
            "X-Idempotency-Key", f"{endorsement_id}-{insurer_id}-{retry_count}"
        )
        return headers

    def _build_request_snapshot(
        self,
        url: str,
        method: str,
        headers: dict[str, str],
        body: Any,
    ) -> AuditLogRequest:
        return AuditLogRequest(
            url=url,
            method=method,
            headers=self._sanitize_headers(headers),
            body=self._mask_sensitive_data(body),
        )

    def _build_response_snapshot(self, response: httpx.Response | None) -> AuditLogResponse | None:
        if not response:
            return None

        return AuditLogResponse(
            status_code=response.status_code,
            headers=self._sanitize_headers(dict(response.headers)),
            body=self._extract_response_body(response),
        )

    def _extract_response_payload(self, response: httpx.Response | None) -> dict[str, Any] | None:
        if not response:
            return None
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": self._extract_response_body(response),
        }

    def _extract_response_body(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        sanitized: dict[str, str] = {}
        for key, value in headers.items():
            if "authorization" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                sanitized[key] = "***"
            else:
                sanitized[key] = value
        return sanitized

    def _mask_sensitive_data(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                key: ("***" if key.lower() in SENSITIVE_KEYS else self._mask_sensitive_data(value))
                for key, value in obj.items()
            }
        if isinstance(obj, list):
            return [self._mask_sensitive_data(value) for value in obj]
        return obj
