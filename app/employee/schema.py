"""Employee Pydantic schemas (DTOs)"""

from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


class EmployeeCreateRequest(BaseModel):
    """Request schema for creating an employee"""

    employer_id: str = Field(..., description="Employer ID")
    employee_code: str = Field(..., min_length=1, max_length=50, description="Employer's internal employee ID")
    demographics: dict[str, Any] = Field(..., description="Employee demographics (DOB, gender, address, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "employer_id": "55qZMH6L4bM006573",
                "employee_code": "E12345",
                "demographics": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "dob": "1990-05-20",
                    "gender": "M",
                    "email": "john.doe@company.com",
                    "address": "123 Main St",
                    "marital_status": "Single",
                },
            }
        }


class EmployeeUpdateRequest(BaseModel):
    """Request schema for updating an employee"""

    employee_code: str | None = Field(None, min_length=1, max_length=50, description="Employer's internal employee ID")
    demographics: dict[str, Any] | None = Field(None, description="Employee demographics")


class EmployeeResponse(BaseModel):
    """Response schema for employee"""

    id: str = Field(..., description="Employee ID")
    employer_id: str = Field(..., description="Employer ID")
    employee_code: str = Field(..., description="Employer's internal employee ID")
    demographics: dict[str, Any] = Field(..., description="Employee demographics")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "55qZMH6L4bM006574",
                "employer_id": "55qZMH6L4bM006573",
                "employee_code": "E12345",
                "demographics": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "dob": "1990-05-20",
                    "gender": "M",
                    "email": "john.doe@company.com",
                },
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }
