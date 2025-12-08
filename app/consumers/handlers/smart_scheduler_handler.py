"""Smart Scheduler handler for ingestion events"""

import json
from typing import Any, List, Dict, Optional

from confluent_kafka import Message

from app.core.adapter.kafka import get_kafka_producer
from app.core.base.handlers import MessageHandler, InterimOutput, handler
from app.core.settings import settings
from app.endorsement_request.service import RequestPriority
from app.utils.logger import get_logger

logger = get_logger(__name__)


@handler("smart_scheduler_handler")
class SmartSchedulerHandler(MessageHandler):
    """
    Handler for endorsement ingestion events.
    Sorts requests by priority before handing the batch to the next stage.
    """

    def __init__(self) -> None:
        self._producer = get_kafka_producer()

    async def handle(self, message: Message, interim_output: InterimOutput) -> InterimOutput:
        """
        Process a single endorsement ingestion message.
        """
        # Reuse bulk logic for single message
        return await self.bulk_handle([message], interim_output)

    async def bulk_handle(self, messages: List[Message], interim_output: InterimOutput) -> InterimOutput:
        """
        Parse and sort messages in-memory using RequestPriority.
        """
        parsed_payloads: List[Dict[str, Any]] = []

        for message in messages:
            try:
                # Parse message value
                value = message.value()
                if isinstance(value, bytes):
                    value = value.decode("utf-8")

                payload = self._parse_json(value)
                if payload is None:
                    continue

                parsed_payloads.append(payload)
            except Exception as exc:
                logger.error("smart_scheduler_handler_error", error=str(exc))
                continue

        if not parsed_payloads:
            return interim_output

        # Sort requests by priority
        sorted_requests = sorted(parsed_payloads, key=self._get_priority)
        interim_output.data.setdefault("sorted_requests", []).extend(sorted_requests)

        self._publish_sorted_requests(sorted_requests)

        logger.debug(
            "smart_scheduler_sorted_batch",
            count=len(sorted_requests),
            first_type=sorted_requests[0].get("type") if sorted_requests else "N/A"
        )

        return interim_output

    def _parse_json(self, value: Any) -> Optional[Dict[str, Any]]:
        """
        Safely parse JSON payloads and emit a warning when parsing fails.
        """
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.error("smart_scheduler_json_error", value=str(value)[:100])
            return None

    def _get_priority(self, payload: Dict[str, Any]) -> int:
        """Compute the priority key for sorting."""
        rtype = payload.get("type", "").upper()
        if rtype == "DELETION":
            return RequestPriority.DELETION
        if rtype == "MODIFICATION":
            return RequestPriority.MODIFICATION
        if rtype == "ADDITION":
            return RequestPriority.ADDITION
        return max(RequestPriority) + 1

    def _publish_sorted_requests(self, sorted_requests: List[Dict[str, Any]]) -> None:
        """
        Publish the ordered requests to the prioritized Kafka topic.
        """
        for payload in sorted_requests:
            try:
                trace_id = payload.get("trace_id") or "smart-scheduler"
                employer_id = payload.get("employer_id")
                endorsement_id = payload.get("endorsement_id")

                headers = {
                    "trace_id": str(trace_id),
                    "source": "smart_scheduler_handler",
                }
                if employer_id is not None:
                    headers["employer_id"] = str(employer_id)

                self._producer.produce(
                    topic=settings.KAFKA_TOPIC_PRIORITIZED,
                    value=payload,
                    key=str(endorsement_id) if endorsement_id is not None else None,
                    headers=headers,
                )
            except Exception as exc:
                logger.error(
                    "smart_scheduler_publish_error",
                    error=str(exc),
                    endorsement_id=payload.get("endorsement_id"),
                )
