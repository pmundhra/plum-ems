"""Audit log MongoDB document model"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLogRequest(BaseModel):
    """Request payload structure for audit logs"""

    url: str
    method: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | str | None = None


class AuditLogResponse(BaseModel):
    """Response payload structure for audit logs"""

    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | str | None = None


class AuditLogError(BaseModel):
    """Error details for audit logs"""

    code: str | None = None
    message: str
    stack_trace: str | None = None


class AuditLogDocument(BaseModel):
    """MongoDB document model for audit logs"""

    # MongoDB will auto-generate _id, but we track our own reference
    endorsement_id: str = Field(..., description="String ID linking to Postgres endorsement_requests.id")
    trace_id: str | None = Field(None, description="OpenTelemetry Trace ID for distributed tracing")
    insurer_id: str = Field(..., description="The target external system (e.g., 'AETNA_01')")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time of the interaction")
    interaction_type: str = Field(
        ..., description="Enum: REST_API, SOAP_XML, SFTP_BATCH"
    )

    # Performance metrics
    latency_ms: float | None = Field(None, description="Time taken for insurer to respond in milliseconds")
    status: str = Field(..., description="Enum: SUCCESS, FAILURE, TIMEOUT")

    # Request we sent
    request: AuditLogRequest | None = None

    # Response we received
    response: AuditLogResponse | None = None

    # Exception details (only if interaction failed)
    error: AuditLogError | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "endorsement_id": "c615...",
                "trace_id": "a1b2...",
                "insurer_id": "AETNA_01",
                "timestamp": "2023-10-01T10:00:00Z",
                "interaction_type": "REST_API",
                "latency_ms": 450,
                "status": "SUCCESS",
                "request": {
                    "url": "https://api.insurer.com/v1/members",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"member": {"firstName": "John"}},
                },
                "response": {
                    "status_code": 200,
                    "headers": {"Date": "Sun, 01 Oct 2023..."},
                    "body": {"confirmationId": "POL-998877", "status": "PROCESSED"},
                },
            }
        }
