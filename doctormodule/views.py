from rest_framework import viewsets, generics
from adminmodule.models import Appointment
from .serializers import AppointmentSerializer
from CareDeskProject.auth import Roles

from django.utils import timezone


from CareDeskProject.auth import IsSameDoctor
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class AppoinmentViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin','Doctor')]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    
    
    
class DoctorAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsSameDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(
            doctor_id=self.kwargs["doctorid"],
            appointment_date= '2026-10-26'
        )