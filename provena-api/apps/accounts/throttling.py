from rest_framework.throttling import UserRateThrottle


class BuyerRateThrottle(UserRateThrottle):
    """1000/hr for buyers only; passes through for other roles so they use their own throttle."""

    scope = "user"

    def allow_request(self, request, view):
        from apps.accounts.models import Role

        if request.user and request.user.is_authenticated and request.user.role == Role.BUYER:
            return super().allow_request(request, view)
        return True


class SupplierRateThrottle(UserRateThrottle):
    """2000/hr for suppliers only."""

    scope = "supplier"

    def allow_request(self, request, view):
        from apps.accounts.models import Role

        if request.user and request.user.is_authenticated and request.user.role == Role.SUPPLIER:
            return super().allow_request(request, view)
        return True


class AdminRateThrottle(UserRateThrottle):
    """Staff users are unconditionally exempt from rate limiting.

    No rate is configured for this class — get_rate() returns None so DRF
    skips enforcement for any non-staff caller too. In practice, admin
    endpoints are protected by IsAdmin, so non-staff never reach them.
    """

    scope = "admin"

    def get_rate(self) -> None:
        return None

    def allow_request(self, request, view) -> bool:
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        return super().allow_request(request, view)
