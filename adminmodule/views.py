from rest_framework import viewsets
from.models import Staff,DoctorDetails, Appointment
from .serializers import StaffSerializer, DoctorSerializer, AppointmentSerializer
from CareDeskProject.auth import Roles
from django.utils import timezone

# Admin module API endpoints for staff, doctor details, and today's appointments.
# These viewsets enforce the project-level role checks before exposing the data.


class StaffViewset(viewsets.ModelViewSet):
    """Manage staff records with admin-only access.

    The admin panel is expected to create, list, update, and delete employee profiles.
    """

    permission_classes = [Roles('Admin')]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer


class DoctorViewset(viewsets.ModelViewSet):
    """Manage doctor detail records with admin-only access."""

    permission_classes = [Roles('Admin')]
    queryset = DoctorDetails.objects.all()
    serializer_class = DoctorSerializer


class AppointmentViewset(viewsets.ModelViewSet):
    """Expose today's appointments for administrators only."""

    permission_classes = [Roles('Admin')]
    queryset = Appointment.objects.filter(appointment_date=timezone.localdate())
    serializer_class = AppointmentSerializer