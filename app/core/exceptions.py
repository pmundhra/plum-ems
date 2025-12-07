"""Custom exception classes"""

from typing import Any

from fastapi import HTTPException, status

from app.schemas.errors import ErrorDetail, ErrorResponse


class APIException(HTTPException):
    """Base exception for all API errors"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: str = "api_error",
        error_code: str = "internal_error",
        details: list[ErrorDetail] | None = None,
        request_id: str | None = None,
    ):
        """
        Initialize API exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_type: Error type category
            error_code: Specific error code
            details: Field-level error details
            request_id: Request ID for tracking
        """
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_type = error_type
        self.error_code = error_code
        self.details = details or []
        self.request_id = request_id

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to ErrorResponse schema"""
        return ErrorResponse(
            type=self.error_type,
            code=self.error_code,
            message=self.message,
            details=self.details,
            request_id=self.request_id,
        )


class ResourceNotFoundError(APIException):
    """Resource not found exception"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        field: str | None = None,
        request_id: str | None = None,
    ):
        message = f"{resource_type} not found: {resource_id}"
        details = [
            ErrorDetail(
                field=field or f"{resource_type.lower()}_id",
                message=message,
                code=f"{resource_type.upper()}_NOT_FOUND",
            )
        ]
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="invalid_request_error",
            error_code="resource_not_found",
            details=details,
            request_id=request_id,
        )


class ValidationError(APIException):
    """Validation error exception"""

    def __init__(
        self,
        message: str = "Request validation failed",
        details: list[ErrorDetail] | None = None,
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="invalid_request_error",
            error_code="validation_error",
            details=details or [],
            request_id=request_id,
        )


class AuthenticationError(APIException):
    """Authentication error exception"""

    def __init__(
        self,
        message: str = "Authentication required",
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="authentication_error",
            error_code="unauthorized",
            request_id=request_id,
        )


class ForbiddenError(APIException):
    """Forbidden access error exception"""

    def __init__(
        self,
        message: str = "Access denied",
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_type="authentication_error",
            error_code="forbidden",
            request_id=request_id,
        )


class RateLimitError(APIException):
    """Rate limit exceeded exception"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_type="rate_limit_error",
            error_code="rate_limit_exceeded",
            request_id=request_id,
        )


class ExternalServiceError(APIException):
    """External service error exception"""

    def __init__(
        self,
        service_name: str,
        message: str | None = None,
        request_id: str | None = None,
    ):
        message = message or f"External service error: {service_name}"
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_type="api_error",
            error_code="external_service_error",
            request_id=request_id,
        )


class ServiceUnavailableError(APIException):
    """Service unavailable exception"""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="api_error",
            error_code="service_unavailable",
            request_id=request_id,
        )


class InternalServerError(APIException):
    """Internal server error exception"""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        request_id: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="api_error",
            error_code="internal_error",
            request_id=request_id,
        )
