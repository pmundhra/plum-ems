"""Kafka handler for ledger check and locking events."""

import json
from typing import Any, Dict

from confluent_kafka import Message

from app.core.base.handlers import MessageHandler, InterimOutput, handler
from app.core.settings import settings
from app.ledger.service import LedgerService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@handler("ledger_handler")
class LedgerHandler(MessageHandler):
    """Routes ledger.check_funds messages to the ledger service."""

    def __init__(self) -> None:
        self._service = LedgerService()

    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        topic = message.topic()
        if topic != settings.KAFKA_TOPIC_LEDGER_CHECK_FUNDS:
            logger.debug("ledger_handler_ignored_topic", topic=topic)
            return interim_output

        payload = self._parse_message(message)
        if payload is None:
            return interim_output

        await self._service.process_check_funds(payload)
        return interim_output

    def _parse_message(self, message: Message) -> Dict[str, Any] | None:
        value = message.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        try:
            return json.loads(value)
        except Exception as exc:
            logger.error(
                "ledger_handler_parse_error",
                error=str(exc),
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )
            return None
