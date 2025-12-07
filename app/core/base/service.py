"""Base service class for business logic"""

from typing import TypeVar, Generic

ModelType = TypeVar("ModelType")


class BaseService(Generic[ModelType]):
    """Base service class for business logic operations"""

    def __init__(self, repository: Any):
        """
        Initialize service.

        Args:
            repository: Repository instance for data access
        """
        self.repository = repository
