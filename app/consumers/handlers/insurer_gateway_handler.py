"""Handler that routes insurer request events to the InsurerGatewayService."""

import asyncio
import json
from typing import Any

from confluent_kafka import Message

from app.core.base.handlers import InterimOutput, MessageHandler, handler
from app.core.settings import settings
from app.insurer_gateway.service import InsurerGatewayService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@handler("insurer_gateway_handler")
class InsurerGatewayHandler(MessageHandler):
    """Routes insurer request topics to the gateway service."""

    def __init__(self) -> None:
        self._service = InsurerGatewayService()
        self._supported_topics = {
            settings.KAFKA_TOPIC_INSURER_REQUEST,
            settings.KAFKA_TOPIC_INSURER_REQUEST_RETRY,
        }

    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        topic = message.topic()
        if topic not in self._supported_topics:
            logger.debug("insurer_gateway_ignored_topic", topic=topic)
            return interim_output

        payload = self._parse_message(message)
        if payload is None:
            return interim_output

        if topic == settings.KAFKA_TOPIC_INSURER_REQUEST_RETRY:
            retry_delay = self._resolve_retry_delay_seconds(payload, message)
            if retry_delay > 0:
                self._schedule_retry(payload, retry_delay)
                return interim_output

        await self._service.process_insurer_request(payload)
        return interim_output

    def _parse_message(self, message: Message) -> dict[str, Any] | None:
        value = message.value()
        if value is None:
            logger.warning(
                "insurer_gateway_empty_payload",
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        try:
            return json.loads(value)
        except Exception as exc:
            logger.error(
                "insurer_gateway_parse_error",
                error=str(exc),
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )
            return None

    def _resolve_retry_delay_seconds(
        self, payload: dict[str, Any], message: Message
    ) -> float:
        delay_value = payload.get("retry_delay_seconds")
        delay_seconds = self._coerce_to_seconds(delay_value)
        if delay_seconds <= 0:
            headers = message.headers() or []
            for key, raw_value in headers:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                if key_str == "retry_after_seconds":
                    header_seconds = self._coerce_to_seconds(raw_value)
                    if header_seconds > 0:
                        delay_seconds = header_seconds
                        break
        return delay_seconds

    def _coerce_to_seconds(self, value: Any) -> float:
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except Exception:
                return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _schedule_retry(self, payload: dict[str, Any], delay_seconds: float) -> None:
        endorsement_id = payload.get("endorsement_id")
        employer_id = payload.get("employer_id")
        logger.info(
            "insurer_gateway_retry_scheduled",
            endorsement_id=endorsement_id,
            employer_id=employer_id,
            delay_seconds=delay_seconds,
        )

        task = asyncio.create_task(
            self._process_retry_after_delay(payload, delay_seconds)
        )
        task.add_done_callback(
            lambda finished_task: self._retry_task_done(
                finished_task, payload, delay_seconds
            )
        )

    async def _process_retry_after_delay(
        self, payload: dict[str, Any], delay_seconds: float
    ) -> None:
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        await self._service.process_insurer_request(payload)

    def _retry_task_done(
        self, task: asyncio.Task[None], payload: dict[str, Any], delay_seconds: float
    ) -> None:
        if task.cancelled():
            logger.warning(
                "insurer_gateway_retry_task_cancelled",
                endorsement_id=payload.get("endorsement_id"),
                employer_id=payload.get("employer_id"),
            )
            return

        exc = task.exception()
        if exc:
            logger.error(
                "insurer_gateway_retry_task_failed",
                endorsement_id=payload.get("endorsement_id"),
                employer_id=payload.get("employer_id"),
                delay_seconds=delay_seconds,
                error=str(exc),
            )
