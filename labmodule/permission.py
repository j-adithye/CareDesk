
from rest_framework.permissions import BasePermission


class IsLabTechnician(BasePermission):
    message = "Only lab technicians can access this API."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "roleid", None)

        if role is None:
            return False

        return role.title.strip().lower().replace(" ", "") == "labtechnician"
