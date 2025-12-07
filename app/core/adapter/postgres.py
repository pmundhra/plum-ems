"""PostgreSQL adapter implementation"""

from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import sessionmaker

from app.core.adapter.postgres_base import PostgresAdapterBase
from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PostgresAdapter(PostgresAdapterBase):
    """PostgreSQL adapter with connection pooling and session management"""

    def __init__(self):
        """Initialize PostgreSQL adapter"""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """Establish connection to PostgreSQL database"""
        if self._is_connected:
            logger.warning("postgres_already_connected")
            return

        try:
            # Create async engine with connection pooling
            self._engine = create_async_engine(
                settings.postgres_url,
                poolclass=QueuePool,
                pool_size=settings.POSTGRES_POOL_SIZE,
                max_overflow=settings.POSTGRES_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before using
                echo=settings.DEBUG,  # Log SQL queries in debug mode
            )

            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )

            self._is_connected = True
            logger.info(
                "postgres_connected",
                pool_size=settings.POSTGRES_POOL_SIZE,
                max_overflow=settings.POSTGRES_MAX_OVERFLOW,
            )
        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def disconnect(self) -> None:
        """Close connection to PostgreSQL database"""
        if not self._is_connected:
            return

        try:
            if self._engine:
                await self._engine.dispose()
            self._session_factory = None
            self._is_connected = False
            logger.info("postgres_disconnected")
        except Exception as e:
            logger.error("postgres_disconnect_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def health_check(self) -> bool:
        """Check if the connection is healthy"""
        if not self._is_connected or not self._engine:
            return False

        try:
            async with self._engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("postgres_health_check_failed", error=str(e))
            return False

    @property
    def is_connected(self) -> bool:
        """Check if adapter is currently connected"""
        return self._is_connected

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session (context manager).

        Usage:
            async with adapter.get_session() as session:
                # Use session
                pass
        """
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Any:
        """
        Execute a raw SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        async with self.get_session() as session:
            result = await session.execute(query, params or {})
            return result

    async def execute_transaction(self, operations: list[callable]) -> Any:
        """
        Execute multiple operations in a transaction.

        Args:
            operations: List of async callables that take a session

        Returns:
            Results from operations
        """
        async with self.get_session() as session:
            results = []
            for operation in operations:
                result = await operation(session)
                results.append(result)
            return results

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get the session factory for dependency injection.

        Returns:
            Session factory
        """
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._session_factory


# Global adapter instance
_postgres_adapter: PostgresAdapter | None = None


def get_postgres_adapter() -> PostgresAdapter:
    """
    Get or create the global PostgreSQL adapter instance.

    Returns:
        PostgresAdapter instance
    """
    global _postgres_adapter
    if _postgres_adapter is None:
        _postgres_adapter = PostgresAdapter()
    return _postgres_adapter


async def init_postgres() -> PostgresAdapter:
    """
    Initialize and connect to PostgreSQL.

    Returns:
        Connected PostgresAdapter instance
    """
    adapter = get_postgres_adapter()
    await adapter.connect()
    return adapter


async def close_postgres() -> None:
    """Close PostgreSQL connection"""
    global _postgres_adapter
    if _postgres_adapter:
        await _postgres_adapter.disconnect()
        _postgres_adapter = None
