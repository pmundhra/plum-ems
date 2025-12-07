"""Redis adapter implementation"""

from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis, ConnectionPool

from app.core.adapter.redis_base import RedisAdapterBase
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisAdapter(RedisAdapterBase):
    """Redis adapter with async connection pooling"""

    def __init__(self):
        """Initialize Redis adapter"""
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """Establish connection to Redis"""
        if self._is_connected:
            logger.warning("redis_already_connected")
            return

        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                max_connections=20,
            )

            # Create Redis client
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            self._is_connected = True
            logger.info(
                "redis_connected",
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
            )
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def disconnect(self) -> None:
        """Close connection to Redis"""
        if not self._is_connected:
            return

        try:
            if self._client:
                await self._client.aclose()
            if self._pool:
                await self._pool.aclose()
            self._is_connected = False
            logger.info("redis_disconnected")
        except Exception as e:
            logger.error("redis_disconnect_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def health_check(self) -> bool:
        """Check if the connection is healthy"""
        if not self._is_connected or not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False

    @property
    def is_connected(self) -> bool:
        """Check if adapter is currently connected"""
        return self._is_connected

    async def get(self, key: str) -> str | None:
        """
        Get a value by key.

        Args:
            key: Redis key

        Returns:
            Value or None if not found
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """
        Set a key-value pair with optional TTL.

        Args:
            key: Redis key
            value: Value to set
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        if ttl:
            return await self._client.setex(key, ttl, value)
        return await self._client.set(key, value)

    async def delete(self, key: str) -> bool:
        """
        Delete a key.

        Args:
            key: Redis key

        Returns:
            True if deleted, False if not found
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        result = await self._client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Redis key

        Returns:
            True if exists, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        result = await self._client.exists(key)
        return result > 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a numeric value.

        Args:
            key: Redis key
            amount: Amount to increment by

        Returns:
            New value after increment
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        return await self._client.incrby(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        return await self._client.expire(key, seconds)

    async def get_connection(self) -> Redis:
        """
        Get the underlying Redis connection.

        Returns:
            Redis client instance
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")

        return self._client


# Global adapter instance
_redis_adapter: RedisAdapter | None = None


def get_redis_adapter() -> RedisAdapter:
    """
    Get or create the global Redis adapter instance.

    Returns:
        RedisAdapter instance
    """
    global _redis_adapter
    if _redis_adapter is None:
        _redis_adapter = RedisAdapter()
    return _redis_adapter


async def init_redis() -> RedisAdapter:
    """
    Initialize and connect to Redis.

    Returns:
        Connected RedisAdapter instance
    """
    adapter = get_redis_adapter()
    await adapter.connect()
    return adapter


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_adapter
    if _redis_adapter:
        await _redis_adapter.disconnect()
        _redis_adapter = None
