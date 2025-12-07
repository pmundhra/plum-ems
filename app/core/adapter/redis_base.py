"""Base Redis adapter interface"""

from typing import Any
from abc import ABC, abstractmethod

from app.core.adapter.base import BaseAdapter


class RedisAdapterBase(BaseAdapter, ABC):
    """Base interface for Redis adapters"""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get a value by key"""
        pass

    @abstractmethod
    async def set(
        self, key: str, value: str, ttl: int | None = None
    ) -> bool:
        """Set a key-value pair with optional TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists"""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value"""
        pass

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key"""
        pass

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get the underlying Redis connection"""
        pass
