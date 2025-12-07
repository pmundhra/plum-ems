"""Distributed locking service using Redis"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from app.core.adapter.redis import get_redis_adapter
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DistributedLock:
    """Distributed lock implementation using Redis"""

    def __init__(self, key: str, timeout: int | None = None):
        """
        Initialize distributed lock.

        Args:
            key: Lock key
            timeout: Lock timeout in seconds (uses default from settings if None)
        """
        self.key = f"lock:{key}"
        self.timeout = timeout or settings.LEDGER_LOCK_TIMEOUT_SECONDS
        self.redis = get_redis_adapter()

    async def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: If True, wait for lock to be available
            timeout: Maximum time to wait for lock (in seconds)

        Returns:
            True if lock acquired, False otherwise
        """
        client = await self.redis.get_connection()
        end_time = None

        if timeout:
            end_time = asyncio.get_event_loop().time() + timeout

        while True:
            # Try to acquire lock using SET with NX (only if not exists) and EX (expiration)
            acquired = await client.set(
                self.key,
                "locked",
                ex=self.timeout,
                nx=True,  # Only set if key doesn't exist
            )

            if acquired:
                logger.debug("lock_acquired", key=self.key, timeout=self.timeout)
                return True

            if not blocking:
                return False

            if end_time and asyncio.get_event_loop().time() >= end_time:
                logger.warning("lock_acquisition_timeout", key=self.key)
                return False

            # Wait a bit before retrying
            await asyncio.sleep(0.1)

    async def release(self) -> bool:
        """
        Release the lock.

        Returns:
            True if lock was released, False if lock didn't exist
        """
        client = await self.redis.get_connection()
        deleted = await self.redis.delete(self.key)

        if deleted:
            logger.debug("lock_released", key=self.key)
        else:
            logger.warning("lock_release_failed", key=self.key, reason="lock_not_found")

        return deleted > 0

    async def extend(self, additional_time: int) -> bool:
        """
        Extend the lock expiration time.

        Args:
            additional_time: Additional seconds to add to lock timeout

        Returns:
            True if lock was extended, False if lock didn't exist
        """
        client = await self.redis.get_connection()
        exists = await self.redis.exists(self.key)

        if exists:
            await self.redis.expire(self.key, self.timeout + additional_time)
            logger.debug("lock_extended", key=self.key, additional_time=additional_time)
            return True

        return False


@asynccontextmanager
async def acquire_lock(
    key: str,
    timeout: int | None = None,
    blocking: bool = True,
    wait_timeout: float | None = None,
):
    """
    Context manager for acquiring and releasing a distributed lock.

    Usage:
        async with acquire_lock("employer:123"):
            # Critical section
            pass

    Args:
        key: Lock key
        timeout: Lock timeout in seconds
        blocking: If True, wait for lock to be available
        wait_timeout: Maximum time to wait for lock acquisition

    Yields:
        Lock instance

    Raises:
        TimeoutError: If lock cannot be acquired within wait_timeout
    """
    lock = DistributedLock(key, timeout)
    acquired = await lock.acquire(blocking=blocking, timeout=wait_timeout)

    if not acquired:
        raise TimeoutError(f"Failed to acquire lock: {key}")

    try:
        yield lock
    finally:
        await lock.release()
