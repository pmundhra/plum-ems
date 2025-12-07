"""Global exception handlers for FastAPI"""

import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import APIException
from app.schemas.errors import ErrorDetail, ErrorWrapper
from app.utils.logger import get_logger
from app.utils.request_id import get_request_id

logger = get_logger(__name__)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle APIException errors.

    Args:
        request: FastAPI request object
        exc: APIException instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = get_request_id(request)
    exc.request_id = request_id

    error_response = exc.to_error_response()
    error_response.request_id = request_id

    logger.error(
        "api_exception",
        error_type=exc.error_type,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorWrapper(error=error_response).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = get_request_id(request)

    # Convert Pydantic errors to ErrorDetail format
    details = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        details.append(
            ErrorDetail(
                field=field_path if field_path else None,
                message=error.get("msg", "Validation error"),
                code=error.get("type", "VALIDATION_ERROR").upper(),
            )
        )

    error_response = ErrorWrapper(
        error={
            "type": "invalid_request_error",
            "code": "validation_error",
            "message": "Request validation failed",
            "details": details,
            "request_id": request_id,
        }
    )

    logger.warning(
        "validation_error",
        errors=exc.errors(),
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """
    Handle FastAPI HTTPException errors.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = get_request_id(request)

    # Determine error type and code based on status code
    status_code = exc.status_code
    if status_code == 401:
        error_type = "authentication_error"
        error_code = "unauthorized"
    elif status_code == 403:
        error_type = "authentication_error"
        error_code = "forbidden"
    elif status_code == 404:
        error_type = "invalid_request_error"
        error_code = "resource_not_found"
    elif status_code == 429:
        error_type = "rate_limit_error"
        error_code = "rate_limit_exceeded"
    else:
        error_type = "api_error"
        error_code = "http_error"

    error_response = ErrorWrapper(
        error={
            "type": error_type,
            "code": error_code,
            "message": str(exc.detail) if hasattr(exc, "detail") else "HTTP error occurred",
            "details": [],
            "request_id": request_id,
        }
    )

    logger.warning(
        "http_exception",
        status_code=status_code,
        detail=str(exc.detail) if hasattr(exc, "detail") else None,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = get_request_id(request)

    # Log full traceback internally
    logger.error(
        "unexpected_error",
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    # Return generic error to client (don't expose internal details)
    error_response = ErrorWrapper(
        error={
            "type": "api_error",
            "code": "internal_error",
            "message": "An unexpected error occurred. Please contact support.",
            "details": [],
            "request_id": request_id,
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )
