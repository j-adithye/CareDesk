from rest_framework import viewsets, generics, status
from adminmodule.models import Appointment, Prescription
from .serializers import AppointmentSerializer, PrescriptionSerializer
from CareDeskProject.auth import Roles

from django.utils import timezone

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from CareDeskProject.auth import IsSameDoctor
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class AppointmentViewset(viewsets.ModelViewSet):
    permission_classes = [Roles('Admin','Doctor')]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    
    
    
class DoctorAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsSameDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(
            doctor_id=self.kwargs["doctorid"],
            appointment_date= timezone.localdate()
        )
        
        
class PrescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doctorid, appointmentid):

        # Verify the logged-in user is the specified doctor
        if (
            request.user.roleid.title.lower() != "doctor"
            or request.user.pk != doctorid
        ):
            return Response(
                {"error": "You are not authorized to write this prescription."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find the appointment belonging to this doctor
        appointment = get_object_or_404(
            Appointment,
            pk=appointmentid,
            doctor_id=doctorid
        )

        # Prevent duplicate prescriptions
        if Prescription.objects.filter(appointment=appointment).exists():
            return Response(
                {"error": "A prescription already exists for this appointment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PrescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(appointment=appointment)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
        
    def get(self, request, doctorid, appointmentid):
        if (
            request.user.roleid.title.lower() != "doctor"
            or request.user.pk != doctorid
        ):
            return Response(
                {"error": "You are not authorized to view this prescription."},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment = get_object_or_404(
            Appointment,
            pk=appointmentid,
            doctor_id=doctorid
        )

        try:
            prescription = Prescription.objects.get(appointment=appointment)
        except Prescription.DoesNotExist:
            return Response(
                {"message": "No prescription exists for this appointment."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PrescriptionSerializer(prescription)
        return Response(serializer.data, status=status.HTTP_200_OK)