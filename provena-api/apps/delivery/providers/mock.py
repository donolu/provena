"""Deterministic courier mock modelled on Uber Direct's API shape (ADR-013).

Mirrors Uber Direct's contract closely (delivery_quotes -> deliveries -> `event.delivery_status`
webhooks) so a real adapter is a drop-in replacement. No network calls. Pass-through at cost:
the buyer fee equals the courier cost.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .base import CourierProvider, Delivery, NotServiceable, Quote

# Dropoff postcodes starting with this are treated as out of the courier's serviceable area,
# so tests (and demos) can exercise the not-serviceable path.
UNSERVICEABLE_PREFIX = "ZZ"

_BASE_FEE = Decimal("3.99")
_PER_ITEM = Decimal("0.50")
QUOTE_TTL = timedelta(minutes=10)

# Uber Direct delivery statuses -> our canonical statuses.
_STATUS_MAP = {
    "pending": "BOOKED",
    "pickup": "EN_ROUTE",
    "pickup_complete": "EN_ROUTE",
    "dropoff": "EN_ROUTE",
    "delivered": "DELIVERED",
    "canceled": "CANCELLED",
    "returned": "FAILED",
    "failed": "FAILED",
}


class MockUberDirectProvider(CourierProvider):
    name = "mock"

    def get_quote(self, *, pickup: dict, dropoff: dict, items: list[dict]) -> Quote:
        postcode = (dropoff.get("postcode") or "").strip().upper()
        if postcode.startswith(UNSERVICEABLE_PREFIX):
            raise NotServiceable(f"Courier delivery is not available to {postcode}.")
        total_units = sum(int(i.get("quantity", 0)) for i in items)
        fee = (_BASE_FEE + _PER_ITEM * total_units).quantize(Decimal("0.01"))
        return Quote(
            provider=self.name,
            quote_id=f"mockq_{uuid.uuid4().hex[:16]}",
            fee=fee,
            courier_cost=fee,  # pass-through at cost
            currency="GBP",
            expires_at=timezone.now() + QUOTE_TTL,
        )

    def create_delivery(
        self, *, quote_id: str, pickup: dict, dropoff: dict, reference: str
    ) -> Delivery:
        delivery_id = f"mockd_{uuid.uuid4().hex[:16]}"
        return Delivery(
            provider=self.name,
            delivery_id=delivery_id,
            status="BOOKED",
            tracking_url=f"https://mock-courier.local/track/{delivery_id}",
        )

    def cancel_delivery(self, delivery_id: str) -> None:
        return None

    def parse_status_event(self, payload: dict) -> tuple[str, str]:
        # Uber Direct: {"kind": "event.delivery_status", "data": {"id": ..., "status": ...}}
        data = payload.get("data", payload)
        delivery_id = data.get("id") or data.get("delivery_id") or ""
        raw = (data.get("status") or "").lower()
        return delivery_id, _STATUS_MAP.get(raw, "EN_ROUTE")

    def simulate_event(self, delivery_id: str, status: str) -> dict:
        """Build a webhook payload for a status transition (tests / manual triggering)."""
        return {"kind": "event.delivery_status", "data": {"id": delivery_id, "status": status}}
