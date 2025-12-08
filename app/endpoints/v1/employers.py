"""Employer API endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import ResourceNotFoundError
from app.core.security.dependencies import require_any_role
from app.core.security.jwt import get_current_user
from app.employer.repository import EmployerRepository
from app.employer.schema import (
    EmployerCreateRequest,
    EmployerUpdateRequest,
    EmployerResponse,
)
from app.schemas.pagination import PaginatedResponse, build_link_header

router = APIRouter(prefix="/employers", tags=["Employers v1"])


@router.post(
    "/",
    response_model=EmployerResponse,
    status_code=201,
    summary="Create employer",
    description="Create a new employer with the provided data. Requires employers:write or employers:admin scope.",
)
async def create_employer(
    request: EmployerCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(
        get_current_user, scopes=["employers:write", "employers:admin"]
    ),
) -> EmployerResponse:
    """Create a new employer (admin only)"""
    repository = EmployerRepository(session)
    
    # Convert config to dict for storage
    employer = await repository.create(
        name=request.name,
        ea_balance=request.ea_balance,
        config=request.config.model_dump(),
        status=request.status,
    )
    
    return EmployerResponse.model_validate(employer)


@router.get(
    "/{id}",
    response_model=EmployerResponse,
    summary="Get employer by ID",
    description="Retrieve an employer by its ID. Requires employers:read scope. Users can only access their own employer unless they have admin scope.",
)
async def get_employer(
    id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employers:read"]),
) -> EmployerResponse:
    """Get employer by ID"""
    repository = EmployerRepository(session)
    employer = await repository.get_by_id_unscoped(id)
    
    if not employer:
        raise ResourceNotFoundError("Employer", id)
    
    # Check authorization: users can only access their own employer unless admin
    user_employer_id = current_user.get("employer_id")
    user_scopes = current_user.get("scopes", [])
    user_roles = current_user.get("roles", [])
    is_admin = "employers:admin" in user_scopes or "admin" in user_roles or "system_admin" in user_roles
    
    if not is_admin and user_employer_id != id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Access denied. You can only access your own employer.")
    
    return EmployerResponse.model_validate(employer)


@router.get(
    "/",
    response_model=PaginatedResponse[EmployerResponse],
    summary="List employers",
    description="List employers with pagination. Requires employers:read scope. Regular users see only their employer. Admins see all employers.",
)
async def list_employers(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employers:read"]),
) -> PaginatedResponse[EmployerResponse]:
    """List employers with pagination"""
    repository = EmployerRepository(session)
    
    user_employer_id = current_user.get("employer_id")
    user_scopes = current_user.get("scopes", [])
    user_roles = current_user.get("roles", [])
    is_admin = "employers:admin" in user_scopes or "admin" in user_roles or "system_admin" in user_roles
    
    if is_admin:
        # Admins can see all employers
        total = await repository.count_unscoped()
        employers = await repository.get_all_unscoped(skip=offset, limit=limit)
    else:
        # Regular users can only see their own employer
        if not user_employer_id:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Access denied. User context missing employer_id.")
        
        # Return single employer if it exists
        employer = await repository.get_by_id_unscoped(user_employer_id)
        total = 1 if employer else 0
        employers = [employer] if employer else []
        # Adjust offset/limit for single item
        if offset > 0 or limit < 1:
            employers = []
    
    # Convert to response models
    data = [EmployerResponse.model_validate(emp) for emp in employers]
    
    # Build pagination response
    paginated_response = PaginatedResponse.create(
        data=data,
        total=total,
        limit=limit,
        offset=offset,
        object_type="employer.list",
    )
    
    # Add headers
    base_url = str(request.url).split("?")[0]
    link_header = build_link_header(base_url, total, limit, offset)
    if link_header:
        response.headers["Link"] = link_header
    response.headers["X-Total-Count"] = str(total)
    
    return paginated_response


@router.put(
    "/{id}",
    response_model=EmployerResponse,
    summary="Update employer",
    description="Update an existing employer by ID. Requires employers:write or employers:admin scope. Users can only update their own employer.",
)
async def update_employer(
    id: str,
    request: EmployerUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(
        get_current_user, scopes=["employers:write", "employers:admin"]
    ),
) -> EmployerResponse:
    """Update employer by ID"""
    repository = EmployerRepository(session)
    
    # Check if employer exists
    existing = await repository.get_by_id_unscoped(id)
    if not existing:
        raise ResourceNotFoundError("Employer", id)
    
    # Check authorization: users can only update their own employer unless admin
    user_employer_id = current_user.get("employer_id")
    user_scopes = current_user.get("scopes", [])
    user_roles = current_user.get("roles", [])
    is_admin = "employers:admin" in user_scopes or "admin" in user_roles or "system_admin" in user_roles
    
    if not is_admin and user_employer_id != id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Access denied. You can only update your own employer.")
    
    # Build update dict (only include provided fields)
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.config is not None:
        update_data["config"] = request.config.model_dump()
    if request.status is not None:
        # Only admins can change status
        if not is_admin:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Access denied. Only admins can change employer status.")
        update_data["status"] = request.status
    
    # Update employer
    updated = await repository.update_unscoped(id, **update_data)
    
    if not updated:
        raise ResourceNotFoundError("Employer", id)
    
    return EmployerResponse.model_validate(updated)
