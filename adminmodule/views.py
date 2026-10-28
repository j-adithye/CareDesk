from rest_framework import viewsets
from.models import Staff
from .serializers import StaffSerializer
from CareDeskProject.auth import Roles
# Create your views here.

class StaffViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    

    