"""HTTP-based strategy for sending insurer requests."""
from __future__ import annotations

import httpx
import traceback
from typing import Any

from app.utils.logger import get_logger
from app.insurer_gateway.strategies.base import GatewayRequest, GatewayResponse, GatewayStrategy

logger = get_logger(__name__)


class HttpGatewayStrategy(GatewayStrategy):
    protocol_name = "REST_API"

    async def execute(self, request: GatewayRequest) -> GatewayResponse:
        response: httpx.Response | None = None
        error_details: dict[str, Any] | None = None
        error_type = "NONE"
        status = "FAILURE"

        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.request(
                    request.config.method,
                    request.request_url,
                    json=request.request_body,
                    headers=request.request_headers,
                )

            if 200 <= response.status_code < 300:
                status = "SUCCESS"
            else:
                status = "FAILURE"
                error_type = "BUSINESS" if 400 <= response.status_code < 500 else "TECHNICAL"
                error_details = {
                    "code": f"HTTP_{response.status_code}",
                    "message": response.text,
                }
        except httpx.RequestError as exc:
            error_type = "TECHNICAL"
            error_details = self._build_exception_error(exc)
            logger.error(
                "insurer_gateway_http_request_error",
                endorsement_id=request.endorsement_id,
                employer_id=request.employer_id,
                error=str(exc),
                trace_id=request.trace_id,
            )
        except Exception as exc:  # pragma: no cover - defensive
            error_type = "TECHNICAL"
            error_details = self._build_exception_error(exc)
            logger.exception(
                "insurer_gateway_http_unhandled_error",
                endorsement_id=request.endorsement_id,
                employer_id=request.employer_id,
                error=str(exc),
                trace_id=request.trace_id,
            )

        return GatewayResponse(
            response=response,
            status=status,
            error_details=error_details,
            error_type=error_type,
        )

    def _build_exception_error(self, exc: Exception) -> dict[str, Any]:
        return {
            "code": exc.__class__.__name__,
            "message": str(exc),
            "stack_trace": traceback.format_exc(),
        }
