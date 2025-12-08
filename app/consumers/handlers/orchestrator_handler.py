"""Kafka handler that orchestrates the endorsement workflow."""

import json
from typing import Any, Dict

from confluent_kafka import Message

from app.core.base.handlers import MessageHandler, InterimOutput, handler
from app.core.settings import settings
from app.endorsement_request.orchestrator import EndorsementOrchestratorService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@handler("orchestrator_handler")
class OrchestratorHandler(MessageHandler):
    """Routes orchestrator-related Kafka topics to the workflow service."""

    def __init__(self) -> None:
        self._service = EndorsementOrchestratorService()
        self._supported_topics = {
            settings.KAFKA_TOPIC_PRIORITIZED,
            settings.KAFKA_TOPIC_LEDGER_FUNDS_LOCKED,
            settings.KAFKA_TOPIC_INSURER_SUCCESS,
        }

    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        topic = message.topic()
        if topic not in self._supported_topics:
            logger.debug("orchestrator_ignored_topic", topic=topic)
            return interim_output

        payload = self._parse_message(message)
        if payload is None:
            return interim_output

        if topic == settings.KAFKA_TOPIC_PRIORITIZED:
            await self._service.handle_prioritized_event(payload)
        elif topic == settings.KAFKA_TOPIC_LEDGER_FUNDS_LOCKED:
            await self._service.handle_funds_locked_event(payload)
        elif topic == settings.KAFKA_TOPIC_INSURER_SUCCESS:
            await self._service.handle_insurer_success_event(payload)

        return interim_output

    def _parse_message(self, message: Message) -> Dict[str, Any] | None:
        value = message.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        try:
            return json.loads(value)
        except Exception as exc:
            logger.error(
                "orchestrator_parse_error",
                error=str(exc),
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )
            return None
