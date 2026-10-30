from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import BasePermission


class IsSameDoctor(BasePermission):
    message = "You can only access your own appointments."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Only users with the Doctor role
        if user.roleid.title.lower() != "doctor":
            return False

        # Check that the URL doctor ID matches the logged-in user's ID
        return str(user.pk) == str(view.kwargs.get("doctorid"))

class LoginSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["role"] = user.roleid.title
        token["roleid"] = user.roleid_id
        token["username"] = user.username

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        return {
            "roleid": self.user.roleid_id,
            "role": self.user.roleid.title,
            "username": self.user.username,
            "access": data["access"],
            "refresh": data["refresh"],
        }


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


def Roles(*roles):

    class RolePermission(BasePermission):
        message = f"Access denied. Required roles: {', '.join(roles)}."

        def has_permission(self, request, view):
            user = request.user

            return bool(
                user
                and user.is_authenticated
                and (
                    user.is_superuser
                    or user.roleid.title in roles
                )
            )

    return RolePermission