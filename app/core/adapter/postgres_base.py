"""Base PostgreSQL adapter interface"""

from typing import Any, AsyncGenerator
from abc import ABC, abstractmethod

from app.core.adapter.base import DatabaseAdapter


class PostgresAdapterBase(DatabaseAdapter, ABC):
    """Base interface for PostgreSQL adapters"""

    @abstractmethod
    async def get_session(self) -> AsyncGenerator[Any, None]:
        """Get an async database session"""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a raw SQL query"""
        pass

    @abstractmethod
    async def execute_transaction(self, operations: list[callable]) -> Any:
        """Execute multiple operations in a transaction"""
        pass
