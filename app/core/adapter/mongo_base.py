"""Base MongoDB adapter interface"""

from typing import Any
from abc import ABC, abstractmethod

from app.core.adapter.base import DatabaseAdapter


class MongoAdapterBase(DatabaseAdapter, ABC):
    """Base interface for MongoDB adapters"""

    @abstractmethod
    def get_database(self, name: str | None = None) -> Any:
        """Get a MongoDB database instance"""
        pass

    @abstractmethod
    def get_collection(self, database_name: str, collection_name: str) -> Any:
        """Get a MongoDB collection"""
        pass

    @abstractmethod
    async def insert_one(self, database: str, collection: str, document: dict[str, Any]) -> str:
        """Insert a single document"""
        pass

    @abstractmethod
    async def find_one(
        self, database: str, collection: str, filter: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Find a single document"""
        pass

    @abstractmethod
    async def find_many(
        self,
        database: str,
        collection: str,
        filter: dict[str, Any] | None = None,
        limit: int | None = None,
        skip: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find multiple documents"""
        pass
