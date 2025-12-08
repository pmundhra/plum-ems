"""Kafka handler that wakes parked endorsement requests."""

import json
from typing import Any

from confluent_kafka import Message

from app.core.base.handlers import InterimOutput, MessageHandler, handler
from app.core.settings import settings
from app.ledger.hold_release import HoldReleaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@handler("hold_release_handler")
class HoldReleaseHandler(MessageHandler):
    """Reconnects `ON_HOLD` requests when the ledger balance increases."""

    def __init__(self) -> None:
        self._service = HoldReleaseService()

    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        topic = message.topic()
        if topic != settings.KAFKA_TOPIC_LEDGER_BALANCE_INCREASED:
            logger.debug("hold_release_ignored_topic", topic=topic)
            return interim_output

        payload = self._parse_message(message)
        if payload is None:
            return interim_output

        await self._service.release_on_hold_requests(payload)
        return interim_output

    def _parse_message(self, message: Message) -> dict[str, Any] | None:
        value = message.value()
        if value is None:
            logger.warning(
                "hold_release_empty_payload",
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
                "hold_release_parse_error",
                error=str(exc),
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )
            return None
