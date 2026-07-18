from functools import lru_cache

from django.conf import settings

from .base import CourierProvider, Delivery, DeliveryStatus, NotServiceable, Quote
from .mock import MockUberDirectProvider

_PROVIDERS = {
    "mock": MockUberDirectProvider,
}

__all__ = [
    "CourierProvider",
    "Delivery",
    "DeliveryStatus",
    "NotServiceable",
    "Quote",
    "get_provider",
]


@lru_cache(maxsize=1)
def get_provider() -> CourierProvider:
    """The configured courier provider (``settings.COURIER_PROVIDER``, default ``"mock"``)."""
    name = getattr(settings, "COURIER_PROVIDER", "mock")
    try:
        return _PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"Unknown COURIER_PROVIDER: {name!r}") from None
