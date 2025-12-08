"""Handler that routes insurer request events to the InsurerGatewayService."""

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
