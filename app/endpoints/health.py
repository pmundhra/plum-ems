"""Health check endpoints"""

from datetime import datetime
from fastapi import APIRouter

from app.core.settings import settings

router = APIRouter()


@router.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        API metadata
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": settings.API_VERSION,
        "status": "operational",
    }


@router.get("/health")
async def health():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/ready")
async def readiness():
    """
    Readiness probe endpoint.

    Returns:
        Readiness status
    """
    # TODO: Add actual readiness checks (database, Redis, Kafka connections)
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/live")
async def liveness():
    """
    Liveness probe endpoint.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
