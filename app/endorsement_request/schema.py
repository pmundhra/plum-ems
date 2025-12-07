"""Endorsement request Pydantic schemas (DTOs)"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class EmployeeData(BaseModel):
    """Employee data in endorsement request"""

    employee_id: str | None = Field(None, description="Employee ID (for existing employees)")
    employee_code: str | None = Field(None, description="Employee code (for new employees)")
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    dob: date | None = Field(None, description="Date of birth")
    gender: str | None = Field(None, description="Gender")
    email: str | None = Field(None, description="Email address")


class CoverageData(BaseModel):
    """Coverage data in endorsement request"""

    plan_id: str = Field(..., description="Plan ID")
    tier: str = Field(..., description="Coverage tier (e.g., EMPLOYEE_ONLY)")
    insurer_id: str = Field(..., description="Insurer ID")


class EndorsementCreateRequest(BaseModel):
    """Request schema for creating an endorsement"""

    employer_id: str = Field(..., description="Employer ID")
    request_type: str = Field(..., description="Endorsement type: ADDITION, DELETION, MODIFICATION")
    effective_date: date = Field(..., description="The 'No Gap' effective date")
    employee: EmployeeData = Field(..., description="Employee information")
    coverage: CoverageData | None = Field(None, description="Coverage details (required for ADDITION)")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "employer_id": "55qZMH6L4bM006573",
                "request_type": "ADDITION",
                "effective_date": "2025-01-01",
                "employee": {
                    "employee_code": "E12345",
                    "first_name": "John",
                    "last_name": "Doe",
                    "dob": "1990-05-20",
                    "gender": "M",
                    "email": "john.doe@company.com",
                },
                "coverage": {
                    "plan_id": "PLAN_GOLD_001",
                    "tier": "EMPLOYEE_ONLY",
                    "insurer_id": "INSURER_A",
                },
                "metadata": {
                    "reason": "New Hire",
                    "department": "Engineering",
                },
            }
        }


class EndorsementResponse(BaseModel):
    """Response schema for endorsement request"""

    id: str = Field(..., description="Endorsement request ID (Tracking ID)")
    employer_id: str = Field(..., description="Employer ID")
    type: str = Field(..., description="Endorsement type")
    status: str = Field(..., description="Current status")
    payload: dict[str, Any] = Field(..., description="Original request payload")
    retry_count: int = Field(..., description="Number of retry attempts")
    effective_date: date = Field(..., description="Effective date")
    trace_id: str | None = Field(None, description="Trace ID for distributed tracing")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "55qZMH6L4bM006576",
                "employer_id": "55qZMH6L4bM006573",
                "type": "ADDITION",
                "status": "RECEIVED",
                "payload": {
                    "employer_id": "55qZMH6L4bM006573",
                    "request_type": "ADDITION",
                    "effective_date": "2025-01-01",
                    "employee": {
                        "employee_code": "E12345",
                        "first_name": "John",
                        "last_name": "Doe",
                    },
                },
                "retry_count": 0,
                "effective_date": "2025-01-01",
                "trace_id": "a1b2c3d4",
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }
