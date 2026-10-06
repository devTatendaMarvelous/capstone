from rest_framework.permissions import BasePermission


class IsAtLeast(BasePermission):
    """Allow the view's roles. Admin and superuser always pass."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, "role", "") == "admin":
            return True
        allowed = getattr(view, "allowed_roles", ())
        return user.role in allowed
