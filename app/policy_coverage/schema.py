"""Policy coverage Pydantic schemas (DTOs)"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyCoverageCreateRequest(BaseModel):
    """Request schema for creating a policy coverage"""

    employee_id: str = Field(..., description="Employee ID")
    insurer_id: str = Field(..., min_length=1, max_length=50, description="Insurer ID")
    status: str = Field(..., description="Policy status (ACTIVE, INACTIVE, PENDING_ISSUANCE)")
    start_date: date = Field(..., description="Coverage start date (No Gap date)")
    end_date: date | None = Field(None, description="Coverage end date (null if active)")
    plan_details: dict[str, Any] | None = Field(None, description="Plan details (plan ID, tier, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": "55qZMH6L4bM006574",
                "insurer_id": "AETNA_01",
                "status": "ACTIVE",
                "start_date": "2025-01-01",
                "end_date": None,
                "plan_details": {
                    "plan_id": "PLAN_GOLD_001",
                    "tier": "EMPLOYEE_ONLY",
                },
            }
        }


class PolicyCoverageUpdateRequest(BaseModel):
    """Request schema for updating a policy coverage"""

    status: str | None = Field(None, description="Policy status")
    end_date: date | None = Field(None, description="Coverage end date")
    plan_details: dict[str, Any] | None = Field(None, description="Plan details")


class PolicyCoverageResponse(BaseModel):
    """Response schema for policy coverage"""

    id: str = Field(..., description="Policy coverage ID")
    employee_id: str = Field(..., description="Employee ID")
    insurer_id: str = Field(..., description="Insurer ID")
    status: str = Field(..., description="Policy status")
    start_date: date = Field(..., description="Coverage start date")
    end_date: date | None = Field(None, description="Coverage end date")
    plan_details: dict[str, Any] | None = Field(None, description="Plan details")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "55qZMH6L4bM006575",
                "employee_id": "55qZMH6L4bM006574",
                "insurer_id": "AETNA_01",
                "status": "ACTIVE",
                "start_date": "2025-01-01",
                "end_date": None,
                "plan_details": {
                    "plan_id": "PLAN_GOLD_001",
                    "tier": "EMPLOYEE_ONLY",
                },
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }
