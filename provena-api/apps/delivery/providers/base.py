"""Provider-agnostic courier interface (ADR-013).

A `CourierProvider` brokers third-party delivery: quote a fee for an address, book a delivery,
cancel it, and interpret status webhooks. Concrete adapters (Uber Direct, Stuart, ...) implement
this; the app selects one via ``settings.COURIER_PROVIDER``. The dataclasses below are the stable
boundary — callers never see a provider's raw payloads.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


class NotServiceable(Exception):
    """The courier cannot deliver to the requested address."""


# Canonical delivery statuses (providers map their own onto these).
class DeliveryStatus:
    QUOTED = "QUOTED"
    BOOKED = "BOOKED"
    EN_ROUTE = "EN_ROUTE"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    CHOICES = [
        (QUOTED, "Quoted"),
        (BOOKED, "Booked"),
        (EN_ROUTE, "En route"),
        (DELIVERED, "Delivered"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    ]
    #: terminal states where no money is owed to the courier / the delivery did not complete
    FAILURE = {FAILED, CANCELLED}


@dataclass
class Quote:
    provider: str
    quote_id: str
    fee: Decimal  # buyer-facing delivery fee (VAT-inclusive); pass-through of courier_cost
    courier_cost: Decimal  # what the platform pays the courier
    currency: str
    expires_at: datetime


@dataclass
class Delivery:
    provider: str
    delivery_id: str
    status: str
    tracking_url: str


class CourierProvider(ABC):
    name: str

    @abstractmethod
    def get_quote(self, *, pickup: dict, dropoff: dict, items: list[dict]) -> Quote:
        """Return a Quote or raise NotServiceable if the address cannot be served."""

    @abstractmethod
    def create_delivery(
        self, *, quote_id: str, pickup: dict, dropoff: dict, reference: str
    ) -> Delivery:
        """Book the delivery against a prior quote."""

    @abstractmethod
    def cancel_delivery(self, delivery_id: str) -> None:
        """Cancel a booked delivery (best effort)."""

    @abstractmethod
    def parse_status_event(self, payload: dict) -> tuple[str, str]:
        """Map a provider webhook payload to ``(delivery_id, canonical_status)``."""
