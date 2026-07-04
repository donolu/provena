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
    """Admins and staff are exempt from rate limiting."""

    scope = "admin"

    def allow_request(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        return True
