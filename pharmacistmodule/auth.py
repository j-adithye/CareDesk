from rest_framework.permissions import BasePermission


# Shared helpers for pharmacist role checks.
# These are used by view permissions and service-layer safeguards.

def user_role_title(user):
    """Return the logged-in user's role title or None when no user is available."""
    if not user or not user.is_authenticated:
        return None
    role = getattr(user, "roleid", None)
    return role.title if role else None


def has_role(user, *roles):
    """Check whether the current user has one of the accepted role titles."""
    return user_role_title(user) in roles


def Roles(*roles):
    """DRF permission: the user's Role title must be one of `roles` (FR-AUTH-09)."""

    class RolePermission(BasePermission):
        """Permission object enforcing a specific staff role requirement."""

        message = f"Not allowed. Required role: {', '.join(roles)}."

        def has_permission(self, request, view):
            """Allow the request only when the user matches one of the allowed roles."""
            return has_role(request.user, *roles)

    return RolePermission
