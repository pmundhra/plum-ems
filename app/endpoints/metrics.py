"""Prometheus metrics endpoint"""

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Response

from app.core.settings import settings

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    """
    Expose Prometheus metrics.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
