"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models to ensure they're registered with SQLAlchemy
# This is required for SQLAlchemy to resolve string-based relationship references
from app.core.database import Base
from app.employer.model import Employer
from app.employee.model import Employee
from app.policy_coverage.model import PolicyCoverage
from app.endorsement_request.model import EndorsementRequest
from app.ledger_transaction.model import LedgerTransaction

from app.core.settings import settings
from app.core.exception_handlers import (
    api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import APIException
from app.endpoints import health, metrics
from app.endpoints.v1 import employers, employees, policy_coverages, endorsements
from app.utils.logger import get_logger
from app.utils.request_id import get_request_id, bind_request_context
from app.core.adapter.postgres import init_postgres, close_postgres
from fastapi import Request
from fastapi.exceptions import RequestValidationError, HTTPException

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Endorsement Management System for Group Insurance",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests"""
    request_id = bind_request_context(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(metrics.router, tags=["Metrics"])

# Include v1 API routers
app.include_router(employers.router, prefix=settings.API_PREFIX)
app.include_router(employees.router, prefix=settings.API_PREFIX)
app.include_router(policy_coverages.router, prefix=settings.API_PREFIX)
app.include_router(endorsements.router, prefix=settings.API_PREFIX)

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    # Initialize database connection
    await init_postgres()
    logger.info(
        "application_started",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    # Close database connection
    await close_postgres()
    logger.info("application_shutdown")
