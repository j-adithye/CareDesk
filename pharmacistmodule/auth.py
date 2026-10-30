from rest_framework.permissions import BasePermission


def user_role_title(user):
    """Role title of a logged-in Staff user (Staff.roleid.title), else None."""
    if not user or not user.is_authenticated:
        return None
    role = getattr(user, "roleid", None)
    return role.title if role else None


def has_role(user, *roles):
    return user_role_title(user) in roles


def Roles(*roles):
    """DRF permission: the user's Role title must be one of `roles` (FR-AUTH-09)."""

    class RolePermission(BasePermission):
        message = f"Not allowed. Required role: {', '.join(roles)}."

        def has_permission(self, request, view):
            return has_role(request.user, *roles)

    return RolePermission
