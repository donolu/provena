from rest_framework.permissions import BasePermission

from .models import SupplierStatus


class IsApprovedSupplier(BasePermission):
    """User is a SUPPLIER role and their profile is approved."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            return request.user.supplier.status == SupplierStatus.APPROVED
        except AttributeError:
            return False


class IsAnySupplier(BasePermission):
    """User is a SUPPLIER role with any profile status (including PENDING)."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return hasattr(request.user, "supplier")
