"""MongoDB adapter implementation"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure

from app.core.adapter.mongo_base import MongoAdapterBase
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MongoAdapter(MongoAdapterBase):
    """MongoDB adapter with async connection management"""

    def __init__(self):
        """Initialize MongoDB adapter"""
        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """Establish connection to MongoDB"""
        if self._is_connected:
            logger.warning("mongo_already_connected")
            return

        try:
            # Create async MongoDB client
            self._client = AsyncIOMotorClient(
                settings.mongo_url,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )

            # Test connection
            await self._client.admin.command("ping")

            # Get database
            self._database = self._client[settings.MONGO_DB]

            self._is_connected = True
            logger.info(
                "mongo_connected",
                host=settings.MONGO_HOST,
                port=settings.MONGO_PORT,
                database=settings.MONGO_DB,
            )
        except ConnectionFailure as e:
            logger.error("mongo_connection_failed", error=str(e), error_type=type(e).__name__)
            raise
        except Exception as e:
            logger.error("mongo_connection_error", error=str(e), error_type=type(e).__name__)
            raise

    async def disconnect(self) -> None:
        """Close connection to MongoDB"""
        if not self._is_connected:
            return

        try:
            if self._client:
                self._client.close()
            self._database = None
            self._is_connected = False
            logger.info("mongo_disconnected")
        except Exception as e:
            logger.error("mongo_disconnect_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def health_check(self) -> bool:
        """Check if the connection is healthy"""
        if not self._is_connected or not self._client:
            return False

        try:
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error("mongo_health_check_failed", error=str(e))
            return False

    @property
    def is_connected(self) -> bool:
        """Check if adapter is currently connected"""
        return self._is_connected

    def get_database(self, name: str | None = None) -> AsyncIOMotorDatabase:
        """
        Get a MongoDB database instance.

        Args:
            name: Database name (uses default if None)

        Returns:
            Database instance
        """
        if not self._client:
            raise RuntimeError("MongoDB not connected. Call connect() first.")

        db_name = name or settings.MONGO_DB
        return self._client[db_name]

    def get_collection(
        self, database_name: str, collection_name: str
    ) -> AsyncIOMotorCollection:
        """
        Get a MongoDB collection.

        Args:
            database_name: Database name
            collection_name: Collection name

        Returns:
            Collection instance
        """
        database = self.get_database(database_name)
        return database[collection_name]

    async def insert_one(
        self, database: str, collection: str, document: dict[str, Any]
    ) -> str:
        """
        Insert a single document.

        Args:
            database: Database name
            collection: Collection name
            document: Document to insert

        Returns:
            Inserted document ID
        """
        coll = self.get_collection(database, collection)
        result = await coll.insert_one(document)
        return str(result.inserted_id)

    async def find_one(
        self, database: str, collection: str, filter: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Find a single document.

        Args:
            database: Database name
            collection: Collection name
            filter: Filter criteria

        Returns:
            Document or None if not found
        """
        coll = self.get_collection(database, collection)
        result = await coll.find_one(filter)
        return result

    async def find_many(
        self,
        database: str,
        collection: str,
        filter: dict[str, Any] | None = None,
        limit: int | None = None,
        skip: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find multiple documents.

        Args:
            database: Database name
            collection: Collection name
            filter: Filter criteria
            limit: Maximum number of documents
            skip: Number of documents to skip

        Returns:
            List of documents
        """
        coll = self.get_collection(database, collection)
        cursor = coll.find(filter or {})

        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        results = await cursor.to_list(length=limit)
        return results


# Global adapter instance
_mongo_adapter: MongoAdapter | None = None


def get_mongo_adapter() -> MongoAdapter:
    """
    Get or create the global MongoDB adapter instance.

    Returns:
        MongoAdapter instance
    """
    global _mongo_adapter
    if _mongo_adapter is None:
        _mongo_adapter = MongoAdapter()
    return _mongo_adapter


async def init_mongo() -> MongoAdapter:
    """
    Initialize and connect to MongoDB.

    Returns:
        Connected MongoAdapter instance
    """
    adapter = get_mongo_adapter()
    await adapter.connect()
    return adapter


async def close_mongo() -> None:
    """Close MongoDB connection"""
    global _mongo_adapter
    if _mongo_adapter:
        await _mongo_adapter.disconnect()
        _mongo_adapter = None
