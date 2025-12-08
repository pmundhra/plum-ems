"""Security dependencies for authorization and scoping"""

from typing import Any

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.core.security.jwt import get_current_user


def get_employer_id_from_user(current_user: dict[str, Any]) -> str:
    """
    Extract employer_id from authenticated user context.
    
    This ensures all employee operations are scoped to the user's employer,
    preventing cross-employer data access.
    
    Args:
        current_user: Authenticated user from JWT token (already validated)
        
    Returns:
        Employer ID from user context
        
    Raises:
        ForbiddenError: If employer_id is not present in user context
    """
    employer_id = current_user.get("employer_id")
    if not employer_id:
        raise ForbiddenError("User context missing employer_id. Access denied.")
    return employer_id


async def require_role(
    required_role: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    FastAPI dependency to require a specific role for access.
    
    Args:
        required_role: Required role (e.g., "admin", "hr_admin", "finance_admin")
        current_user: Authenticated user from JWT token
        
    Returns:
        User information if authorized
        
    Raises:
        ForbiddenError: If user doesn't have required role
    """
    roles = current_user.get("roles", [])
    if required_role not in roles:
        raise ForbiddenError(
            f"Access denied. Required role: {required_role}"
        )
    return current_user


def require_any_role(allowed_roles: list[str]):
    """
    Factory function to create a FastAPI dependency that requires any of the specified roles.
    
    Usage:
        @router.post("/")
        async def endpoint(
            current_user: dict = Depends(require_any_role(["admin", "hr_admin"]))
        ):
            ...
    
    Args:
        allowed_roles: List of allowed roles
        
    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        roles = current_user.get("roles", [])
        if not any(role in roles for role in allowed_roles):
            raise ForbiddenError(
                f"Access denied. Required one of: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker
