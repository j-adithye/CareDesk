
from rest_framework.permissions import BasePermission


# Permission used by lab endpoints to ensure only lab technicians can access them.
class IsLabTechnician(BasePermission):
    """Allow access only to users whose role title is Lab Technician."""

    message = "Only lab technicians can access this API."

    def has_permission(self, request, view):
        """Validate that the caller is an authenticated lab technician."""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "roleid", None)

        if role is None:
            return False

        # Compare normalized role titles because the stored value may include spaces.
        return role.title.strip().lower().replace(" ", "") == "labtechnician"
