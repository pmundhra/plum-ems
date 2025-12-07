"""Base validator class"""

from typing import Any
from pydantic import BaseModel, ValidationError


class BaseValidator:
    """Base validator for business rule validation"""

    @staticmethod
    def validate_model(data: dict[str, Any], model_class: type[BaseModel]) -> BaseModel:
        """
        Validate data against a Pydantic model.

        Args:
            data: Data dictionary to validate
            model_class: Pydantic model class

        Returns:
            Validated model instance

        Raises:
            ValidationError: If validation fails
        """
        return model_class(**data)

    @staticmethod
    def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> None:
        """
        Validate that required fields are present.

        Args:
            data: Data dictionary
            required_fields: List of required field names

        Raises:
            ValueError: If any required field is missing
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
