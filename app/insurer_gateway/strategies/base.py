"""Core strategy interfaces for the insurer gateway."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.settings.base import InsurerGatewayConfigEntry


@dataclass
class GatewayRequest:
    endorsement_id: str
    employer_id: str
    trace_id: str | None
    kafka_payload: dict[str, Any]
    retry_count: int
    request_body: dict[str, Any]
    request_headers: dict[str, str]
    request_url: str
    timeout_seconds: int
    config: InsurerGatewayConfigEntry


@dataclass
class GatewayResponse:
    response: Any | None
    status: str
    error_details: dict[str, Any] | None
    error_type: str


class GatewayStrategy(ABC):
    """Allows plugging various insurer interaction strategies."""

    protocol_name: str = ""

    @abstractmethod
    async def execute(self, request: GatewayRequest) -> GatewayResponse:
        """Execute the interaction for the given request context."""
        raise NotImplementedError()
