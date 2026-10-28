from rest_framework import viewsets
from.models import Staff,DoctorDetails
from .serializers import StaffSerializer, DoctorSerializer
from CareDeskProject.auth import Roles
# Create your views here.

class StaffViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    
class DoctorViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = DoctorDetails.objects.all()
    serializer_class = DoctorSerializer
    