"""JWT authentication utilities"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from app.core.settings import settings
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2 scheme with scopes support
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token",
    scopes={
        "employers:read": "Read employer information",
        "employers:write": "Create and update employers",
        "employers:admin": "Full employer administration",
        "employees:read": "Read employee information",
        "employees:write": "Create and update employees",
        "ledger:read": "Read ledger information",
        "ledger:write": "Manage ledger transactions",
        "endorsements:read": "Read endorsement information",
        "endorsements:write": "Create and manage endorsements",
    },
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


async def get_current_user(
    security_scopes: SecurityScopes,  # Injected by FastAPI Security()
    token: str = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from JWT token with scope validation.

    Args:
        security_scopes: SecurityScopes object containing required scopes for the endpoint (injected by FastAPI Security)
        token: JWT token from Authorization header (injected by FastAPI)

    Returns:
        User information from token including:
        - user_id: User identifier
        - email: User email
        - roles: List of user roles
        - employer_id: Employer ID the user belongs to (if applicable)
        - scopes: List of scopes from token

    Raises:
        AuthenticationError: If token is missing or invalid
        ForbiddenError: If token doesn't have required scopes
    """
    if not token:
        raise AuthenticationError("Authentication required")
    
    # Clean token: remove any leading "Bearer " prefix if accidentally included
    # This handles cases where Authorization header might be "Bearer Bearer <token>"
    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        # Extract scopes from token (can be in "scope" or "scopes" field)
        token_scopes = payload.get("scopes", [])
        if isinstance(token_scopes, str):
            # Handle space-separated scopes string
            token_scopes = token_scopes.split()
        elif not isinstance(token_scopes, list):
            token_scopes = []

        # Validate required scopes
        if security_scopes.scopes:
            missing_scopes = [
                scope for scope in security_scopes.scopes if scope not in token_scopes
            ]
            if missing_scopes:
                raise ForbiddenError(
                    f"Insufficient permissions. Required scopes: {', '.join(security_scopes.scopes)}. "
                    f"Missing: {', '.join(missing_scopes)}"
                )

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "employer_id": payload.get("employer_id"),  # Extract employer_id from token
            "scopes": token_scopes,  # Include scopes in user context
        }
    except (AuthenticationError, ForbiddenError):
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
        # Create a dummy SecurityScopes object for get_current_user
        class DummyScopes:
            scopes = []
        return await get_current_user(DummyScopes(), token)
    except AuthenticationError:
        return None
