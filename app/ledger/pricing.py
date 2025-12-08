"""Stubbed pricing client for endorsement requests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from app.core.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LedgerPricingClient:
    """
    Temporarily stubbed pricing client for endorsement requests.

    This should eventually call a dedicated pricing API or rules engine.
    """

    def __init__(self, pricing_map: Mapping[str, Decimal] | None = None) -> None:
        source = pricing_map or settings.LEDGER_ENDORSEMENT_PRICING
        self._pricing: dict[str, Decimal] = {
            key.upper(): Decimal(str(value)) for key, value in source.items()
        }
        self._default = self._pricing.get("ADDITION", Decimal("0"))

    async def get_endorsement_price(
        self,
        request_type: str,
        context: Mapping[str, Any] | None = None,
    ) -> Decimal:
        """
        Return the stubbed price for the given endorsement type.

        Args:
            request_type: The endorsement request type (Addition/Deletion/Modification).
            context: Optional payload context for future enhancement.
        """
        normalized = (request_type or "ADDITION").upper()
        price = self._pricing.get(normalized, self._default)

        logger.debug(
            "ledger_pricing_stub",
            request_type=normalized,
            price=str(price),
            note="Stubbed pricing; replace with real implementation when available",
            context=context or {},
        )

        return price
