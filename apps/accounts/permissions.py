from rest_framework.permissions import BasePermission

from .models import Role


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == Role.ADMIN
        )


class IsSupplier(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == Role.SUPPLIER
        )


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == Role.BUYER
        )


class IsAdminOrSupplier(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.SUPPLIER)
        )
