"""JWT authentication utilities"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.settings import settings
from app.core.exceptions import AuthenticationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token",
    auto_error=False,  # We'll handle errors manually
)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise AuthenticationError("Invalid or expired token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header

    Returns:
        User information from token

    Raises:
        AuthenticationError: If token is missing or invalid
    """
    if not token:
        raise AuthenticationError("Authentication required")

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
        }
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("auth_token_validation_failed", error=str(e), error_type=type(e).__name__)
        raise AuthenticationError("Token validation failed")


async def get_optional_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any] | None:
    """
    FastAPI dependency to optionally get current user (doesn't raise if missing).

    Args:
        token: JWT token from Authorization header

    Returns:
        User information or None if not authenticated
    """
    if not token:
        return None

    try:
        return await get_current_user(token)
    except AuthenticationError:
        return None
