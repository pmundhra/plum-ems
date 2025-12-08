"""JWT authentication utilities"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt

# Lazy import settings to avoid Python 3.14 compatibility issues with pydantic-settings
_settings = None


def _get_settings():
    """Lazy load settings to avoid import-time issues with Python 3.14"""
    global _settings
    if _settings is None:
        try:
            from app.core.settings import settings as _settings_module
            _settings = _settings_module
        except (TypeError, AssertionError, ImportError) as e:
            # If settings can't be loaded, raise a helpful error
            raise RuntimeError(
                f"Cannot load settings due to Python 3.14 compatibility issue: {e}. "
                "Please use create_access_token_with_config() instead."
            )
    return _settings


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
    expire_minutes: int | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        secret_key: Optional secret key (defaults to settings.SECRET_KEY)
        algorithm: Optional algorithm (defaults to settings.ALGORITHM)
        expire_minutes: Optional expiration in minutes (defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Get settings if not provided
    if secret_key is None or algorithm is None or (expires_delta is None and expire_minutes is None):
        try:
            settings = _get_settings()
            secret_key = secret_key or settings.SECRET_KEY
            algorithm = algorithm or settings.ALGORITHM
            if expires_delta is None:
                expire_minutes = expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        except RuntimeError:
            # If settings can't be loaded, require all parameters
            if secret_key is None:
                raise ValueError("secret_key is required when settings cannot be loaded")
            if algorithm is None:
                raise ValueError("algorithm is required when settings cannot be loaded")
            if expires_delta is None and expire_minutes is None:
                raise ValueError("expires_delta or expire_minutes is required when settings cannot be loaded")

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes or 30)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string
        secret_key: Optional secret key (defaults to settings.SECRET_KEY)
        algorithm: Optional algorithm (defaults to settings.ALGORITHM)

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    # Get settings if not provided
    if secret_key is None or algorithm is None:
        try:
            settings = _get_settings()
            secret_key = secret_key or settings.SECRET_KEY
            algorithm = algorithm or settings.ALGORITHM
        except RuntimeError:
            if secret_key is None:
                raise ValueError("secret_key is required when settings cannot be loaded")
            if algorithm is None:
                raise ValueError("algorithm is required when settings cannot be loaded")

    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError as e:
        if logger:
            logger.warning("jwt_decode_failed", error=str(e))
        raise AuthenticationError("Invalid or expired token")


# Lazy import logger and exceptions to avoid triggering settings import
try:
    from app.core.exceptions import AuthenticationError, ForbiddenError
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except (TypeError, AssertionError, ImportError):
    # Fallback if imports fail due to Python 3.14 issues
    class AuthenticationError(Exception):
        pass
    class ForbiddenError(Exception):
        pass
    logger = None

# FastAPI imports - handle Python 3.14 compatibility issues
# We catch the specific error and retry with a workaround
try:
    from fastapi import Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer, SecurityScopes
    _FASTAPI_IMPORT_ERROR = None
except (TypeError, AssertionError) as e:
    # Python 3.14 compatibility issue - try workaround
    _FASTAPI_IMPORT_ERROR = e
    try:
        # Try importing via importlib as a workaround
        import importlib
        import sys
        
        # Force reload typing if needed
        if 'typing' in sys.modules:
            importlib.reload(sys.modules['typing'])
        
        fastapi_mod = importlib.import_module('fastapi')
        security_mod = importlib.import_module('fastapi.security')
        
        Depends = fastapi_mod.Depends
        HTTPException = fastapi_mod.HTTPException
        status = fastapi_mod.status
        OAuth2PasswordBearer = security_mod.OAuth2PasswordBearer
        SecurityScopes = security_mod.SecurityScopes
        _FASTAPI_IMPORT_ERROR = None
    except Exception as e2:
        logger.error(
            "fastapi_import_failed_after_workaround",
            original_error=str(_FASTAPI_IMPORT_ERROR),
            workaround_error=str(e2),
            error_type=type(e2).__name__,
        )
        # Set to None so functions will raise RuntimeError if used
        Depends = None
        HTTPException = None
        status = None
        OAuth2PasswordBearer = None
        SecurityScopes = None
except ImportError as e:
    _FASTAPI_IMPORT_ERROR = e
    Depends = None
    HTTPException = None
    status = None
    OAuth2PasswordBearer = None
    SecurityScopes = None

# Initialize OAuth2 scheme only if FastAPI imports succeeded
if OAuth2PasswordBearer is not None:
    try:
        _settings_obj = _get_settings()
        api_prefix = _settings_obj.API_PREFIX
    except RuntimeError:
        api_prefix = "/api/v1"  # Default fallback
    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl=f"{api_prefix}/auth/token",
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
else:
    oauth2_scheme = None


async def get_current_user(
    security_scopes: SecurityScopes,  # Injected by FastAPI Security()
    token: str = Depends(oauth2_scheme) if Depends and oauth2_scheme else None,  # type: ignore
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
        RuntimeError: If FastAPI is not available
    """
    if Depends is None or oauth2_scheme is None:
        raise RuntimeError(
            f"FastAPI is not available. Cannot use get_current_user. "
            f"Original error: {_FASTAPI_IMPORT_ERROR}"
        )
    
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
        if hasattr(security_scopes, "scopes") and security_scopes.scopes:
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


async def get_optional_user(
    token: str = Depends(oauth2_scheme) if Depends and oauth2_scheme else None  # type: ignore
) -> dict[str, Any] | None:
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
