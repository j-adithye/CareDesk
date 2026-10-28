from rest_framework.permissions import BasePermission   # parent class for custom permission rules


class IsReceptionist(BasePermission):                    # our own rule; DRF runs it on every request
    message = "Only receptionists can access this endpoint."   # text shown in the 403 response

    def has_permission(self, request, view):             # DRF calls this; True = allow, False = 403
        user = request.user                              # the Staff user found from the token
        return bool(                                     # bool() makes sure we return True or False
            user                                         # a user object exists
            and user.is_authenticated                    # and the user is logged in
            and user.roleid.title == "Receptionist"      # roleid points to a Role row, .title is its name
        )