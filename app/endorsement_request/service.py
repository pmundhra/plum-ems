"""Endorsement request service for business logic and scheduling"""

import json
import time
from datetime import datetime
from enum import IntEnum
from typing import Any, List

from app.core.adapter.kafka import get_kafka_producer
from app.core.adapter.redis import get_redis_adapter
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestPriority(IntEnum):
    """Priority levels for endorsement types (Lower value = Higher Priority)"""
    DELETION = 1      # Process credits first (releases funds)
    MODIFICATION = 2  # Neutral/Mixed
    ADDITION = 3      # Process debits last (consumes funds)


class SmartSchedulerService:
    """
    Service to buffer, prioritize, and schedule endorsement requests.
    Uses a 'Tumbling Window' approach per employer.
    """

    def __init__(self):
        self.redis = get_redis_adapter()
        self.producer = get_kafka_producer()

    async def buffer_request(self, employer_id: str, request_data: dict[str, Any]) -> None:
        """
        Add a request to the employer's processing buffer.
        
        Args:
            employer_id: The employer ID
            request_data: The full endorsement request data
        """
        await self.buffer_batch(employer_id, [request_data])

    async def buffer_batch(self, employer_id: str, request_data_list: list[dict[str, Any]]) -> None:
        """
        Add multiple requests to the employer's processing buffer.
        
        Args:
            employer_id: The employer ID
            request_data_list: List of endorsement request data
        """
        if not request_data_list:
            return

        queue_key = f"scheduler:queue:{employer_id}"
        window_key = f"scheduler:window:{employer_id}"
        active_set_key = "scheduler:active_employers"

        redis = await self.redis.get_connection()
        
        # Use pipeline for atomic batch push
        async with redis.pipeline(transaction=True) as pipe:
            # Add all requests to Redis queue
            json_payloads = [json.dumps(data) for data in request_data_list]
            pipe.rpush(queue_key, *json_payloads)
            
            # Mark employer as active
            pipe.sadd(active_set_key, employer_id)
            
            await pipe.execute()

        # Check if window exists, if not start one (outside transaction to avoid complexity)
        # We can optimize this by checking local cache or just blindly setting if not exists
        # using SET NX.
        window_expiry = await redis.get(window_key)
        if not window_expiry:
            # Start new window
            expiry_time = int(time.time()) + settings.SCHEDULER_WINDOW_SECONDS
            # Use SET NX to ensure we don't overwrite if another process set it concurrently
            if await redis.set(window_key, str(expiry_time), nx=True):
                logger.info(
                    "scheduler_window_started",
                    employer_id=employer_id,
                    window_seconds=settings.SCHEDULER_WINDOW_SECONDS
                )

    async def process_ready_windows(self) -> int:
        """
        Check all active employers and process those whose windows have expired.
        
        Returns:
            Number of batches processed
        """
        active_set_key = "scheduler:active_employers"
        
        # Get all active employers
        # smembers returns a set of bytes
        redis = await self.redis.get_connection()
        active_employers_bytes = await redis.smembers(active_set_key)
        active_employers = [e.decode('utf-8') if isinstance(e, bytes) else e for e in active_employers_bytes]

        processed_count = 0
        current_time = int(time.time())

        for employer_id in active_employers:
            window_key = f"scheduler:window:{employer_id}"
            window_expiry_str = await self.redis.get(window_key)

            # If no window key, maybe it was processed or expired? 
            # Or if current_time >= expiry, process it.
            should_process = False
            if window_expiry_str:
                if current_time >= int(window_expiry_str):
                    should_process = True
            else:
                # No window key but in active set? Process immediately.
                should_process = True

            if should_process:
                await self._process_batch(employer_id)
                processed_count += 1

        return processed_count

    async def _process_batch(self, employer_id: str) -> None:
        """
        Process a single employer's batch: Sort and Publish.
        """
        queue_key = f"scheduler:queue:{employer_id}"
        window_key = f"scheduler:window:{employer_id}"
        active_set_key = "scheduler:active_employers"
        redis = await self.redis.get_connection()

        # Fetch all items (and clear queue atomically-ish)
        # Using multi/exec pipeline or just lrange + delete
        # For strict safety, we should use RENAME or a Lua script, but lrange+del is okay for MVP 
        # provided we handle the race where new items arrive between get and del.
        # Better: LPOP loop or LRANGE 0 -1 then LTRIM.
        # LTRIM is risky if new items added.
        # Safe way: RENAME to a temp key, then process temp key.
        
        temp_key = f"scheduler:processing:{employer_id}:{time.time()}"
        
        # Rename queue to temp key to "lock" current items
        try:
            # Check if queue exists first
            if not await self.redis.exists(queue_key):
                # Nothing to process, clean up
                await redis.delete(window_key)
                await redis.srem(active_set_key, employer_id)
                return

            await redis.rename(queue_key, temp_key)
        except Exception as e:
            logger.warning("scheduler_rename_failed", error=str(e), employer_id=employer_id)
            # Maybe queue was empty or concurrent access?
            return

        # Clear window and active status
        await redis.delete(window_key)
        await redis.srem(active_set_key, employer_id)

        # Read items from temp key
        items_bytes = await redis.lrange(temp_key, 0, -1)
        await redis.delete(temp_key)

        if not items_bytes:
            return

        requests = []
        for item in items_bytes:
            try:
                requests.append(json.loads(item))
            except json.JSONDecodeError:
                logger.error("scheduler_json_parse_error", item=item)
                continue

        # Sort Logic: DELETION (Credit) < MODIFICATION < ADDITION (Debit)
        def get_priority(req):
            rtype = req.get("type", "").upper()
            if rtype == "DELETION":
                return RequestPriority.DELETION
            elif rtype == "MODIFICATION":
                return RequestPriority.MODIFICATION
            elif rtype == "ADDITION":
                return RequestPriority.ADDITION
            return 99 # Unknown

        # Sort in-place
        requests.sort(key=get_priority)

        # Publish ordered batch
        logger.info(
            "scheduler_processing_batch",
            employer_id=employer_id,
            count=len(requests),
            first_type=requests[0].get("type") if requests else "N/A"
        )

        for req in requests:
            try:
                # Ensure trace_id is passed
                trace_id = req.get("trace_id") or "scheduler-generated"
                endorsement_id = req.get("endorsement_id")
                
                self.producer.produce(
                    topic=settings.KAFKA_TOPIC_PRIORITIZED,
                    value=req,
                    key=endorsement_id, # Keep partitioning by endorsement/employer
                    headers={
                        "trace_id": trace_id,
                        "employer_id": employer_id,
                        "source": "smart_scheduler"
                    }
                )
            except Exception as e:
                logger.error("scheduler_publish_failed", error=str(e), endorsement_id=req.get("endorsement_id"))
