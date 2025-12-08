"""Employee API endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import ResourceNotFoundError
from app.core.security.dependencies import get_employer_id_from_user
from app.core.security.jwt import get_current_user
from app.employee.repository import EmployeeRepository
from app.employee.schema import (
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    EmployeeResponse,
)
from app.schemas.pagination import PaginatedResponse, build_link_header
from app.employer.repository import EmployerRepository

router = APIRouter(prefix="/employees", tags=["Employees v1"])


@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=201,
    summary="Create employee",
    description="Create a new employee. Requires employees:write scope. The employer_id in the request must match the authenticated user's employer_id.",
)
async def create_employee(
    request: EmployeeCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:write"]),
) -> EmployeeResponse:
    """Create a new employee (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    # Validate that request employer_id matches authenticated user's employer_id
    if request.employer_id != employer_id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError(
            "Access denied. You can only create employees for your own employer."
        )
    
    # Verify employer exists
    employer_repo = EmployerRepository(session)
    employer = await employer_repo.get_by_id_unscoped(employer_id)
    if not employer:
        raise ResourceNotFoundError("Employer", employer_id)
    
    repository = EmployeeRepository(session)
    
    # Check if employee_code already exists for this employer
    existing = await repository.get_by_employee_code(
        employer_id, request.employee_code
    )
    if existing:
        from app.core.exceptions import ValidationError
        from app.schemas.errors import ErrorDetail
        raise ValidationError(
            message=f"Employee with code '{request.employee_code}' already exists for this employer",
            details=[
                ErrorDetail(
                    field="employee_code",
                    message="Employee code must be unique per employer",
                    code="DUPLICATE_EMPLOYEE_CODE",
                )
            ],
        )
    
    employee = await repository.create(
        employer_id=employer_id,  # Use employer_id from authenticated user context
        employee_code=request.employee_code,
        demographics=request.demographics,
    )
    
    return EmployeeResponse.model_validate(employee)


@router.get(
    "/{id}",
    response_model=EmployeeResponse,
    summary="Get employee by ID",
    description="Retrieve an employee by its ID. Requires employees:read scope. The employer_id is taken from the authenticated user's context.",
)
async def get_employee(
    id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:read"]),
) -> EmployeeResponse:
    """Get employee by ID (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    repository = EmployeeRepository(session)
    employee = await repository.get_by_id(id, employer_id=employer_id)
    
    if not employee:
        raise ResourceNotFoundError("Employee", id)
    
    return EmployeeResponse.model_validate(employee)


@router.get(
    "/",
    response_model=PaginatedResponse[EmployeeResponse],
    summary="List employees",
    description="List employees with pagination. Requires employees:read scope. The employer_id is taken from the authenticated user's context.",
)
async def list_employees(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:read"]),
) -> PaginatedResponse[EmployeeResponse]:
    """List employees with pagination (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    # Verify employer exists
    employer_repo = EmployerRepository(session)
    employer = await employer_repo.get_by_id_unscoped(employer_id)
    if not employer:
        raise ResourceNotFoundError("Employer", employer_id)
    
    repository = EmployeeRepository(session)
    
    # Get total count
    total = await repository.count(employer_id=employer_id)
    
    # Get paginated results
    employees = await repository.get_by_employer_id(
        employer_id=employer_id, skip=offset, limit=limit
    )
    
    # Convert to response models
    data = [EmployeeResponse.model_validate(emp) for emp in employees]
    
    # Build pagination response
    paginated_response = PaginatedResponse.create(
        data=data,
        total=total,
        limit=limit,
        offset=offset,
        object_type="employee.list",
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
    response_model=EmployeeResponse,
    summary="Update employee",
    description="Update an existing employee by ID. Requires employees:write scope. The employer_id is taken from the authenticated user's context.",
)
async def update_employee(
    id: str,
    request: EmployeeUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:write"]),
) -> EmployeeResponse:
    """Update employee by ID (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    repository = EmployeeRepository(session)
    
    # Check if employee exists
    existing = await repository.get_by_id(id, employer_id=employer_id)
    if not existing:
        raise ResourceNotFoundError("Employee", id)
    
    # Check for duplicate employee_code if being updated
    if request.employee_code is not None and request.employee_code != existing.employee_code:
        duplicate = await repository.get_by_employee_code(employer_id, request.employee_code)
        if duplicate and duplicate.id != id:
            from app.core.exceptions import ValidationError
            from app.schemas.errors import ErrorDetail
            raise ValidationError(
                message=f"Employee with code '{request.employee_code}' already exists for this employer",
                details=[
                    ErrorDetail(
                        field="employee_code",
                        message="Employee code must be unique per employer",
                        code="DUPLICATE_EMPLOYEE_CODE",
                    )
                ],
            )
    
    # Build update dict (only include provided fields)
    update_data = {}
    if request.employee_code is not None:
        update_data["employee_code"] = request.employee_code
    if request.demographics is not None:
        update_data["demographics"] = request.demographics
    
    # Update employee
    updated = await repository.update(id, employer_id=employer_id, **update_data)
    
    if not updated:
        raise ResourceNotFoundError("Employee", id)
    
    return EmployeeResponse.model_validate(updated)
