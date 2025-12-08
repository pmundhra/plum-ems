"""Employer Pydantic schemas (DTOs)"""

from decimal import Decimal
from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


class DefaultPolicyConfig(BaseModel):
    """Default policy configuration for employer"""

    insurer_id: str = Field(..., description="Default Insurer ID")
    plan_id: str = Field(..., description="Default Plan ID")
    tier: str = Field(..., description="Default Coverage tier")


class EmployerConfig(BaseModel):
    """Employer configuration schema"""

    low_balance_threshold: float = Field(..., description="Low balance alert threshold")
    notification_email: str | None = Field(None, description="Email for notifications")
    allowed_overdraft: bool = Field(default=False, description="Whether overdraft is allowed")
    default_policy: DefaultPolicyConfig | None = Field(None, description="Default policy configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "low_balance_threshold": 1000.00,
                "notification_email": "finance@abc.xyz",
                "allowed_overdraft": False,
                "default_policy": {
                    "insurer_id": "AETNA_01",
                    "plan_id": "PLAN_GOLD_001",
                    "tier": "EMPLOYEE_ONLY"
                }
            }
        }


class EmployerCreateRequest(BaseModel):
    """Request schema for creating an employer"""

    name: str = Field(..., min_length=1, max_length=255, description="Legal name of the company")
    ea_balance: Decimal = Field(default=Decimal("0.00"), description="Initial Endorsement Account balance")
    config: EmployerConfig = Field(..., description="Employer configuration")
    status: str = Field(default="ACTIVE", description="Employer status")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "ea_balance": 10000.00,
                "config": {
                    "low_balance_threshold": 1000.00,
                    "notification_email": "finance@acme.com",
                    "allowed_overdraft": False,
                    "default_policy": {
                        "insurer_id": "AETNA_01",
                        "plan_id": "PLAN_GOLD_001",
                        "tier": "EMPLOYEE_ONLY"
                    }
                },
                "status": "ACTIVE",
            }
        }


class EmployerUpdateRequest(BaseModel):
    """Request schema for updating an employer"""

    name: str | None = Field(None, min_length=1, max_length=255, description="Legal name of the company")
    config: EmployerConfig | None = Field(None, description="Employer configuration")
    status: str | None = Field(None, description="Employer status")


class EmployerResponse(BaseModel):
    """Response schema for employer"""

    id: str = Field(..., description="Employer ID")
    name: str = Field(..., description="Legal name of the company")
    ea_balance: Decimal = Field(..., description="Current Endorsement Account balance")
    config: EmployerConfig = Field(..., description="Employer configuration")
    status: str = Field(..., description="Employer status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "55qZMH6L4bM006573",
                "name": "Acme Corporation",
                "ea_balance": 10000.00,
                "config": {
                    "low_balance_threshold": 1000.00,
                    "notification_email": "finance@acme.com",
                    "allowed_overdraft": False,
                    "default_policy": {
                        "insurer_id": "AETNA_01",
                        "plan_id": "PLAN_GOLD_001",
                        "tier": "EMPLOYEE_ONLY"
                    }
                },
                "status": "ACTIVE",
                "created_at": "2025-01-27T10:00:00Z",
                "updated_at": "2025-01-27T10:00:00Z",
            }
        }
