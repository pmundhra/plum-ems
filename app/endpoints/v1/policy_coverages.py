"""Policy Coverage API endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.security.dependencies import get_employer_id_from_user
from app.core.security.jwt import get_current_user
from app.employee.repository import EmployeeRepository
from app.policy_coverage.repository import PolicyCoverageRepository
from app.policy_coverage.schema import (
    PolicyCoverageCreateRequest,
    PolicyCoverageUpdateRequest,
    PolicyCoverageResponse,
)
from app.schemas.pagination import PaginatedResponse, build_link_header
from app.schemas.errors import ErrorDetail

router = APIRouter(prefix="/policy-coverages", tags=["Policy Coverages v1"])


@router.post(
    "/",
    response_model=PolicyCoverageResponse,
    status_code=201,
    summary="Create policy coverage",
    description="Create a new policy coverage for an employee. Requires appropriate scope. The employer_id is taken from the authenticated user's context.",
)
async def create_policy_coverage(
    request: PolicyCoverageCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:write"]),
) -> PolicyCoverageResponse:
    """Create a new policy coverage (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    
    # Verify employee exists and belongs to the employer
    employee_repo = EmployeeRepository(session)
    employee = await employee_repo.get_by_id(request.employee_id, employer_id=employer_id)
    if not employee:
        raise ResourceNotFoundError("Employee", request.employee_id)
    
    repository = PolicyCoverageRepository(session)
    
    # Validate status
    valid_statuses = ["ACTIVE", "INACTIVE", "PENDING_ISSUANCE"]
    if request.status not in valid_statuses:
        raise ValidationError(
            message=f"Invalid status: {request.status}",
            details=[
                ErrorDetail(
                    field="status",
                    message=f"Status must be one of: {', '.join(valid_statuses)}",
                    code="INVALID_STATUS",
                )
            ],
        )
    
    # Validate dates
    if request.end_date and request.end_date < request.start_date:
        raise ValidationError(
            message="end_date must be after or equal to start_date",
            details=[
                ErrorDetail(
                    field="end_date",
                    message="End date must be after or equal to start date",
                    code="INVALID_DATE_RANGE",
                )
            ],
        )
    
    # Create policy coverage
    policy_coverage = await repository.create(
        employer_id=employer_id,
        employee_id=request.employee_id,
        insurer_id=request.insurer_id,
        status=request.status,
        start_date=request.start_date,
        end_date=request.end_date,
        plan_details=request.plan_details,
    )
    
    return PolicyCoverageResponse.model_validate(policy_coverage)


@router.get(
    "/{id}",
    response_model=PolicyCoverageResponse,
    summary="Get policy coverage by ID",
    description="Retrieve a policy coverage by its ID. Requires appropriate scope. The employer_id is taken from the authenticated user's context.",
)
async def get_policy_coverage(
    id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:read"]),
) -> PolicyCoverageResponse:
    """Get policy coverage by ID (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    repository = PolicyCoverageRepository(session)
    policy_coverage = await repository.get_by_id(id, employer_id=employer_id)
    
    if not policy_coverage:
        raise ResourceNotFoundError("PolicyCoverage", id)
    
    return PolicyCoverageResponse.model_validate(policy_coverage)


@router.get(
    "/",
    response_model=PaginatedResponse[PolicyCoverageResponse],
    summary="List policy coverages",
    description="List policy coverages with pagination. Requires appropriate scope. The employer_id is taken from the authenticated user's context. Can filter by employee_id or insurer_id.",
)
async def list_policy_coverages(
    request: Request,
    response: Response,
    employee_id: str | None = Query(None, description="Filter by employee ID"),
    insurer_id: str | None = Query(None, description="Filter by insurer ID"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:read"]),
) -> PaginatedResponse[PolicyCoverageResponse]:
    """List policy coverages with pagination (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    repository = PolicyCoverageRepository(session)
    
    # Apply filters
    if employee_id:
        # Verify employee belongs to employer
        employee_repo = EmployeeRepository(session)
        employee = await employee_repo.get_by_id(employee_id, employer_id=employer_id)
        if not employee:
            raise ResourceNotFoundError("Employee", employee_id)
        
        # Get coverages for this employee
        policy_coverages = await repository.get_by_employee_id(
            employer_id=employer_id, employee_id=employee_id, skip=offset, limit=limit
        )
        # Count total for this employee (simplified - could be optimized)
        all_coverages = await repository.get_by_employee_id(
            employer_id=employer_id, employee_id=employee_id, skip=0, limit=10000
        )
        total = len(all_coverages)
    elif insurer_id:
        # Get coverages for this insurer
        policy_coverages = await repository.get_by_insurer_id(
            employer_id=employer_id, insurer_id=insurer_id, skip=offset, limit=limit
        )
        # Count total for this insurer (simplified - could be optimized)
        all_coverages = await repository.get_by_insurer_id(
            employer_id=employer_id, insurer_id=insurer_id, skip=0, limit=10000
        )
        total = len(all_coverages)
    else:
        # Get all coverages for employer
        policy_coverages = await repository.get_all(
            employer_id=employer_id, skip=offset, limit=limit
        )
        total = await repository.count(employer_id=employer_id)
    
    # Convert to response models
    data = [PolicyCoverageResponse.model_validate(pc) for pc in policy_coverages]
    
    # Build pagination response
    paginated_response = PaginatedResponse.create(
        data=data,
        total=total,
        limit=limit,
        offset=offset,
        object_type="policy_coverage.list",
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
    response_model=PolicyCoverageResponse,
    summary="Update policy coverage",
    description="Update an existing policy coverage by ID. Requires appropriate scope. The employer_id is taken from the authenticated user's context.",
)
async def update_policy_coverage(
    id: str,
    request: PolicyCoverageUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(get_current_user, scopes=["employees:write"]),
) -> PolicyCoverageResponse:
    """Update policy coverage by ID (scoped to authenticated user's employer)"""
    employer_id = get_employer_id_from_user(current_user)
    repository = PolicyCoverageRepository(session)
    
    # Check if policy coverage exists
    existing = await repository.get_by_id(id, employer_id=employer_id)
    if not existing:
        raise ResourceNotFoundError("PolicyCoverage", id)
    
    # Validate status if provided
    if request.status is not None:
        valid_statuses = ["ACTIVE", "INACTIVE", "PENDING_ISSUANCE"]
        if request.status not in valid_statuses:
            raise ValidationError(
                message=f"Invalid status: {request.status}",
                details=[
                    ErrorDetail(
                        field="status",
                        message=f"Status must be one of: {', '.join(valid_statuses)}",
                        code="INVALID_STATUS",
                    )
                ],
            )
    
    # Validate dates if provided
    if request.end_date is not None and request.end_date < existing.start_date:
        raise ValidationError(
            message="end_date must be after or equal to start_date",
            details=[
                ErrorDetail(
                    field="end_date",
                    message="End date must be after or equal to start date",
                    code="INVALID_DATE_RANGE",
                )
            ],
        )
    
    # Build update dict (only include provided fields)
    update_data = {}
    if request.status is not None:
        update_data["status"] = request.status
    if request.end_date is not None:
        update_data["end_date"] = request.end_date
    if request.plan_details is not None:
        update_data["plan_details"] = request.plan_details
    
    # Update policy coverage
    updated = await repository.update(id, employer_id=employer_id, **update_data)
    
    if not updated:
        raise ResourceNotFoundError("PolicyCoverage", id)
    
    return PolicyCoverageResponse.model_validate(updated)
