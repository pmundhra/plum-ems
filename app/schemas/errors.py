"""Error response schemas"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Field-level error detail"""

    field: str | None = Field(None, description="Field name with error")
    message: str = Field(..., description="Specific error message")
    code: str = Field(..., description="Error code for this field")


class ErrorResponse(BaseModel):
    """Standardized error response format"""

    type: str = Field(..., description="Error type category")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] = Field(default_factory=list, description="Field-level error details")
    request_id: str | None = Field(None, description="Request ID for tracking")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "invalid_request_error",
                "code": "validation_error",
                "message": "Request validation failed",
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "INVALID_FORMAT",
                    }
                ],
                "request_id": "req_123abc",
                "timestamp": "2025-01-27T10:00:00Z",
            }
        }


class ErrorWrapper(BaseModel):
    """Wrapper for error response"""

    error: ErrorResponse

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_not_found",
                    "message": "Resource not found",
                    "details": [],
                    "request_id": "req_123abc",
                    "timestamp": "2025-01-27T10:00:00Z",
                }
            }
        }
