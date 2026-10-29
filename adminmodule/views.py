from rest_framework import viewsets
from.models import Staff,DoctorDetails, Appointment
from .serializers import StaffSerializer, DoctorSerializer, AppointmentSerializer
from CareDeskProject.auth import Roles
from django.utils import timezone

# Create your views here.

class StaffViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    
class DoctorViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = DoctorDetails.objects.all()
    serializer_class = DoctorSerializer
    
    
class AppointmentViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin')]
    queryset = Appointment.objects.filter(appointment_date= timezone.localdate())
    serializer_class = AppointmentSerializer