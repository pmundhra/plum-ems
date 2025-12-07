"""Request ID utilities for logging and tracing"""

import uuid
from typing import Optional

from fastapi import Request


def get_request_id(request: Request) -> str:
    """
    Extract or generate a request ID from the request headers.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    return request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")


def set_request_id(request_id: str) -> None:
    """
    Set request ID in context for structured logging.

    Args:
        request_id: Request ID to set in context
    """
    import structlog.contextvars

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)


def bind_request_context(request: Request, user_id: Optional[str] = None) -> str:
    """
    Bind request context variables for structured logging.

    Args:
        request: FastAPI request object
        user_id: Optional user ID if authenticated

    Returns:
        Request ID string
    """
    import structlog.contextvars

    request_id = get_request_id(request)
    context_vars = {"request_id": request_id}

    if user_id:
        context_vars["user_id"] = user_id

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**context_vars)

    return request_id
