"""Validation service for business rules and duplicate detection"""

import hashlib
import json
from typing import Any

from app.core.adapter.redis import get_redis_adapter
from app.core.exceptions import ValidationError
from app.schemas.errors import ErrorDetail
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationService:
    """Service for validation logic"""

    def __init__(self):
        """Initialize validation service"""
        self.redis = get_redis_adapter()

    async def check_duplicate(self, employer_id: str, payload: dict[str, Any]) -> None:
        """
        Check if the same request has been received within 24 hours.

        Args:
            employer_id: Employer ID
            payload: Request payload

        Raises:
            ValidationError: If duplicate is detected
        """
        # Create deterministic hash of the payload
        # We sort keys to ensure {a:1, b:2} produces same hash as {b:2, a:1}
        # We use default=str to handle date/datetime objects that might be in the payload
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        key = f"dedup:{employer_id}:{payload_hash}"

        # Use the underlying redis client to perform atomic set-if-not-exists
        # This prevents race conditions where two identical requests arrive simultaneously
        redis_client = await self.redis.get_connection()
        
        # set(name, value, ex=seconds, nx=True) returns True if set, None if not set
        is_new = await redis_client.set(key, "1", ex=86400, nx=True)

        if not is_new:
            logger.warning("duplicate_request_detected", employer_id=employer_id, hash=payload_hash)
            raise ValidationError(
                message="Duplicate request detected",
                details=[
                    ErrorDetail(
                        field="payload",
                        message="This request was already submitted within the last 24 hours.",
                        code="DUPLICATE_REQUEST",
                    )
                ],
            )
