from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == Role.ADMIN


class IsDisputePartyOrAdmin(BasePermission):
    """Only the opener, respondent, or an admin may access the dispute."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == Role.ADMIN:
            return True
        return obj.opened_by_id == user.id or obj.respondent_id == user.id
