"""Endorsement ingestion API endpoints"""

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Request, Security, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.core.security.dependencies import get_employer_id_from_user
from app.core.security.jwt import get_current_user
from app.endorsement_request.model import EndorsementRequest
from app.endorsement_request.repository import EndorsementRequestRepository
from app.endorsement_request.schema import (
    EndorsementCreateRequest,
    EndorsementResponse,
)
from app.employer.repository import EmployerRepository
from app.schemas.errors import ErrorDetail
from app.utils.logger import get_logger
from app.utils.request_id import get_request_id

# Kafka imports
from app.core.adapter.kafka import get_kafka_producer

logger = get_logger(__name__)

router = APIRouter(prefix="/endorsements", tags=["Endorsements v1"])

# Kafka topic for ingested endorsements
KAFKA_TOPIC_INGESTED = "endorsement.ingested"


def validate_endorsement_request(
    request: EndorsementCreateRequest,
    employer_id: str,
    default_policy: dict[str, Any] | None = None,
) -> None:
    """
    Validate endorsement request business rules.

    Args:
        request: Endorsement creation request
        employer_id: Authenticated user's employer ID
        default_policy: Employer's default policy configuration (optional)

    Raises:
        ValidationError: If validation fails
    """
    errors: list[ErrorDetail] = []

    # Validate employer_id matches authenticated user's employer
    if request.employer_id != employer_id:
        errors.append(
            ErrorDetail(
                field="employer_id",
                message="Access denied. You can only create endorsements for your own employer.",
                code="FORBIDDEN_EMPLOYER",
            )
        )

    # Validate coverage is required for ADDITION
    if request.request_type == "ADDITION" and not request.coverage and not default_policy:
        errors.append(
            ErrorDetail(
                field="coverage",
                message="Coverage details are required for ADDITION requests when no default policy is configured",
                code="MISSING_COVERAGE",
            )
        )

    if errors:
        raise ValidationError(
            message="Endorsement request validation failed",
            details=errors,
        )


@router.post(
    "/",
    response_model=EndorsementResponse,
    status_code=201,
    summary="Create single endorsement",
    description="Submit a request to add, remove, or modify an employee's coverage. Requires endorsements:write scope.",
)
async def create_endorsement(
    request: EndorsementCreateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(
        get_current_user, scopes=["endorsements:write"]
    ),
) -> EndorsementResponse:
    """
    Create a single endorsement request.

    The request is validated, stored in the database with status RECEIVED,
    and published to Kafka topic 'endorsement.ingested' for further processing.
    """
    employer_id = get_employer_id_from_user(current_user)
    trace_id = get_request_id(http_request)

    logger.info(
        "endorsement_creation_started",
        employer_id=employer_id,
        request_type=request.request_type,
        trace_id=trace_id,
    )

    # Validate employer exists
    employer_repo = EmployerRepository(session)
    employer = await employer_repo.get_by_id_unscoped(employer_id)
    if not employer:
        raise ResourceNotFoundError("Employer", employer_id)

    # Get default policy from employer config
    default_policy = employer.config.get("default_policy")

    # Validate business rules
    validate_endorsement_request(request, employer_id, default_policy)

    # Convert request to dict for payload storage
    # Use mode='json' to serialize dates and other non-JSON types to strings
    payload = request.model_dump(mode='json')

    # If coverage is missing for ADDITION and we have default policy, populate it in payload
    if request.request_type == "ADDITION" and not request.coverage and default_policy:
        payload["coverage"] = default_policy

    # Create endorsement request
    endorsement_repo = EndorsementRequestRepository(session)
    endorsement = await endorsement_repo.create(
        employer_id=employer_id,
        type=request.request_type,
        status="RECEIVED",
        payload=payload,
        retry_count=0,
        effective_date=request.effective_date,
        trace_id=trace_id,
    )

    # Commit transaction
    await session.commit()

    logger.info(
        "endorsement_created",
        endorsement_id=endorsement.id,
        employer_id=employer_id,
        request_type=request.request_type,
        trace_id=trace_id,
    )

    # Publish to Kafka for async processing
    try:
        kafka_producer = get_kafka_producer()
        kafka_message = {
            "endorsement_id": endorsement.id,
            "employer_id": employer_id,
            "type": request.request_type,
            "effective_date": request.effective_date.isoformat(),
            "trace_id": trace_id,
            "payload": payload,
        }
        await kafka_producer.produce(
            topic=KAFKA_TOPIC_INGESTED,
            value=kafka_message,
            key=endorsement.id,  # Use endorsement ID as key for partitioning
            headers={"trace_id": trace_id, "employer_id": employer_id},
        )
        logger.info(
            "endorsement_published_to_kafka",
            endorsement_id=endorsement.id,
            topic=KAFKA_TOPIC_INGESTED,
            trace_id=trace_id,
        )
    except Exception as e:
        # Log error but don't fail the request - the endorsement is already created
        logger.error(
            "kafka_publish_failed",
            endorsement_id=endorsement.id,
            error=str(e),
            error_type=type(e).__name__,
            trace_id=trace_id,
        )

    return EndorsementResponse.model_validate(endorsement)


@router.post(
    "/batch",
    status_code=202,
    summary="Batch endorsement upload",
    description="Upload a CSV or JSON file for bulk endorsement processing. Requires endorsements:write scope.",
)
async def batch_upload_endorsements(
    http_request: Request,
    file: UploadFile = File(..., description="CSV or JSON file containing endorsement requests"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, Any] = Security(
        get_current_user, scopes=["endorsements:write"]
    ),
) -> dict[str, Any]:
    """
    Process batch upload of endorsement requests from CSV or JSON file.

    Returns a summary with batch_id, status, and message.
    """
    employer_id = get_employer_id_from_user(current_user)
    trace_id = get_request_id(http_request)

    logger.info(
        "batch_upload_started",
        employer_id=employer_id,
        filename=file.filename,
        content_type=file.content_type,
        trace_id=trace_id,
    )

    # Validate employer exists
    employer_repo = EmployerRepository(session)
    employer = await employer_repo.get_by_id_unscoped(employer_id)
    if not employer:
        raise ResourceNotFoundError("Employer", employer_id)

    # Get default policy from employer config
    default_policy = employer.config.get("default_policy")

    # Validate file type
    if not file.filename:
        raise ValidationError(
            message="File name is required",
            details=[
                ErrorDetail(
                    field="file",
                    message="File name must be provided",
                    code="MISSING_FILENAME",
                )
            ],
        )

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in {"csv", "json"}:
        raise ValidationError(
            message="Invalid file type",
            details=[
                ErrorDetail(
                    field="file",
                    message="File must be CSV or JSON format",
                    code="INVALID_FILE_TYPE",
                )
            ],
        )

    # Read file content
    content = await file.read()
    if not content:
        raise ValidationError(
            message="File is empty",
            details=[
                ErrorDetail(
                    field="file",
                    message="Uploaded file contains no data",
                    code="EMPTY_FILE",
                )
            ],
        )

    # Parse file based on type
    endorsement_requests: list[EndorsementCreateRequest] = []
    errors: list[dict[str, Any]] = []

    try:
        if file_extension == "json":
            # Parse JSON file
            try:
                data = json.loads(content.decode("utf-8"))
                if not isinstance(data, list):
                    raise ValidationError(
                        message="JSON file must contain an array of endorsement requests",
                        details=[
                            ErrorDetail(
                                field="file",
                                message="Root element must be an array",
                                code="INVALID_JSON_STRUCTURE",
                            )
                        ],
                    )

                for idx, item in enumerate(data):
                    try:
                        req = EndorsementCreateRequest.model_validate(item)
                        # Override employer_id with authenticated user's employer_id
                        req.employer_id = employer_id
                        validate_endorsement_request(req, employer_id, default_policy)
                        endorsement_requests.append(req)
                    except Exception as e:
                        errors.append(
                            {
                                "row": idx + 1,
                                "error": str(e),
                                "data": item,
                            }
                        )
            except json.JSONDecodeError as e:
                raise ValidationError(
                    message="Invalid JSON format",
                    details=[
                        ErrorDetail(
                            field="file",
                            message=f"JSON parsing error: {str(e)}",
                            code="INVALID_JSON",
                        )
                    ],
                )

        else:  # CSV
            import csv
            import io

            # Parse CSV file
            csv_content = content.decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            for idx, row in enumerate(csv_reader):
                try:
                    # Convert CSV row to endorsement request
                    # Note: This is a simplified parser - you may need to adjust based on CSV format
                    req_dict = {
                        "employer_id": employer_id,
                        "request_type": row.get("request_type", "").upper(),
                        "effective_date": row.get("effective_date", ""),
                        "employee": {
                            "employee_id": row.get("employee_id") or None,
                            "employee_code": row.get("employee_code") or None,
                            "first_name": row.get("first_name") or None,
                            "last_name": row.get("last_name") or None,
                            "dob": row.get("dob") or None,
                            "gender": row.get("gender") or None,
                            "email": row.get("email") or None,
                        },
                    }

                    # Add coverage if provided
                    if row.get("plan_id"):
                        req_dict["coverage"] = {
                            "plan_id": row.get("plan_id", ""),
                            "tier": row.get("tier", ""),
                            "insurer_id": row.get("insurer_id", ""),
                        }

                    req = EndorsementCreateRequest.model_validate(req_dict)
                    validate_endorsement_request(req, employer_id, default_policy)
                    endorsement_requests.append(req)
                except Exception as e:
                    errors.append(
                        {
                            "row": idx + 2,  # +2 because row 1 is header, and enumerate starts at 0
                            "error": str(e),
                            "data": row,
                        }
                    )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "batch_file_parsing_failed",
            error=str(e),
            error_type=type(e).__name__,
            trace_id=trace_id,
        )
        raise ValidationError(
            message="Failed to parse file",
            details=[
                ErrorDetail(
                    field="file",
                    message=f"File parsing error: {str(e)}",
                    code="FILE_PARSING_ERROR",
                )
            ],
        )

    if not endorsement_requests:
        raise ValidationError(
            message="No valid endorsement requests found in file",
            details=[
                ErrorDetail(
                    field="file",
                    message="File must contain at least one valid endorsement request",
                    code="NO_VALID_REQUESTS",
                )
            ],
        )

    # Create endorsement requests
    endorsement_repo = EndorsementRequestRepository(session)
    created_endorsements: list[EndorsementRequest] = []
    kafka_producer = get_kafka_producer()

    for req in endorsement_requests:
        try:
            # Use mode='json' to serialize dates and other non-JSON types to strings
            payload = req.model_dump(mode='json')

            # If coverage is missing for ADDITION and we have default policy, populate it in payload
            if req.request_type == "ADDITION" and not req.coverage and default_policy:
                payload["coverage"] = default_policy

            endorsement = await endorsement_repo.create(
                employer_id=employer_id,
                type=req.request_type,
                status="RECEIVED",
                payload=payload,
                retry_count=0,
                effective_date=req.effective_date,
                trace_id=trace_id,
            )
            created_endorsements.append(endorsement)

            # Publish to Kafka
            try:
                kafka_message = {
                    "endorsement_id": endorsement.id,
                    "employer_id": employer_id,
                    "type": req.request_type,
                    "effective_date": req.effective_date.isoformat(),
                    "trace_id": trace_id,
                    "payload": payload,
                }
                await kafka_producer.produce(
                    topic=KAFKA_TOPIC_INGESTED,
                    value=kafka_message,
                    key=endorsement.id,
                    headers={"trace_id": trace_id, "employer_id": employer_id},
                )
            except Exception as e:
                logger.error(
                    "kafka_publish_failed_in_batch",
                    endorsement_id=endorsement.id,
                    error=str(e),
                    trace_id=trace_id,
                )
        except Exception as e:
            errors.append(
                {
                    "endorsement": req.model_dump(),
                    "error": str(e),
                }
            )

    # Commit all transactions
    await session.commit()

    # Generate batch ID (using first endorsement ID as batch identifier)
    batch_id = created_endorsements[0].id if created_endorsements else trace_id

    logger.info(
        "batch_upload_completed",
        batch_id=batch_id,
        total_processed=len(endorsement_requests),
        successful=len(created_endorsements),
        errors=len(errors),
        trace_id=trace_id,
    )

    response = {
        "batch_id": batch_id,
        "status": "PROCESSING",
        "message": f"File accepted. {len(created_endorsements)} records queued.",
        "total_processed": len(endorsement_requests),
        "successful": len(created_endorsements),
        "errors": len(errors),
    }

    if errors:
        response["error_details"] = errors

    return response
