"""Base adapter classes for database connections"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Base class for all database adapters"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the database"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the database"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the connection is healthy"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if adapter is currently connected"""
        pass


class DatabaseAdapter(BaseAdapter):
    """Base class for database adapters with session management"""

    @abstractmethod
    async def get_session(self) -> Any:
        """Get a database session"""
        pass

    @abstractmethod
    async def close_session(self, session: Any) -> None:
        """Close a database session"""
        pass
