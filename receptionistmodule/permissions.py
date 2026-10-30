from rest_framework.permissions import BasePermission   # parent class for custom permission rules


# Custom permission used by receptionist endpoints.
# It checks that the caller is authenticated and has the Receptionist role.
class IsReceptionist(BasePermission):
    """Allow access only to staff members assigned the Receptionist role."""

    message = "Only receptionists can access this endpoint."   # text shown in the 403 response

    def has_permission(self, request, view):
        """Return True only when the current user is an authenticated receptionist."""
        user = request.user                              # the Staff user found from the token
        return bool(
            user                                         # a user object exists
            and user.is_authenticated                    # and the user is logged in
            and user.roleid.title == "Receptionist"      # roleid points to a Role row, .title is its name
        )