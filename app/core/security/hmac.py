"""HMAC signature verification for webhook security"""

import hmac
import hashlib
from typing import Any

from fastapi import Request, HTTPException, status

from app.core.settings import settings
from app.core.exceptions import AuthenticationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_hmac_signature(payload: str | bytes, secret: str) -> str:
    """
    Generate HMAC SHA-256 signature for a payload.

    Args:
        payload: Payload to sign (string or bytes)
        secret: Secret key for signing

    Returns:
        Hexadecimal signature string
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return signature


def verify_hmac_signature(
    payload: str | bytes,
    received_signature: str,
    secret: str,
) -> bool:
    """
    Verify HMAC SHA-256 signature.

    Args:
        payload: Original payload
        received_signature: Signature received in header
        secret: Secret key for verification

    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_hmac_signature(payload, secret)

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, received_signature)


async def verify_webhook_signature(request: Request) -> None:
    """
    FastAPI dependency to verify HMAC signature for webhook requests.

    Args:
        request: FastAPI request object

    Raises:
        AuthenticationError: If signature is missing or invalid
    """
    # Get signature from header
    signature_header = request.headers.get("X-Insurer-Signature")
    if not signature_header:
        logger.warning("webhook_signature_missing", path=request.url.path)
        raise AuthenticationError("Missing signature header")

    # Extract signature value (format: "sha256=<signature>")
    if signature_header.startswith("sha256="):
        received_signature = signature_header[7:]  # Remove "sha256=" prefix
    else:
        received_signature = signature_header

    # Read request body
    body = await request.body()

    # Verify signature
    is_valid = verify_hmac_signature(body, received_signature, settings.HMAC_SECRET_KEY)

    if not is_valid:
        logger.warning(
            "webhook_signature_invalid",
            path=request.url.path,
            received_signature=received_signature[:20] + "...",  # Log partial for debugging
        )
        raise AuthenticationError("Invalid signature")

    logger.debug("webhook_signature_verified", path=request.url.path)


def get_hmac_dependency() -> Any:
    """
    Get HMAC verification dependency for FastAPI routes.

    Returns:
        Dependency function
    """
    return verify_webhook_signature
