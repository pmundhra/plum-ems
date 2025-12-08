"""Helper utilities for ledger Kafka events."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.core.adapter.kafka import get_kafka_producer
from app.core.metrics import KAFKA_MESSAGES_PRODUCED
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def publish_balance_increase(
    employer_id: str,
    change_amount: Decimal,
    new_balance: Decimal,
    source: str | None = None,
) -> None:
    """Publish an event when the employer's balance grows."""

    payload: dict[str, str] = {
        "employer_id": employer_id,
        "change_amount": str(change_amount),
        "new_balance": str(new_balance),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if source:
        payload["source"] = source

    try:
        get_kafka_producer().produce(
            topic=settings.KAFKA_TOPIC_LEDGER_BALANCE_INCREASED,
            value=payload,
            key=employer_id,
        )
        KAFKA_MESSAGES_PRODUCED.labels(
            topic=settings.KAFKA_TOPIC_LEDGER_BALANCE_INCREASED
        ).inc()
    except Exception as exc:  # pragma: no cover - logging best effort
        logger.error(
            "ledger_balance_increase_publish_failed",
            employer_id=employer_id,
            change_amount=str(change_amount),
            error=str(exc),
        )
