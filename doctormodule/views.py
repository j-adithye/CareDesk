from rest_framework import viewsets, generics, status
from .models import Appointment, Prescription, LabResult, PrescriptionMedicine
from .serializers import AppointmentSerializer, PrescriptionSerializer
from CareDeskProject.auth import Roles

from django.utils import timezone

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from CareDeskProject.auth import IsSameDoctor
from rest_framework.permissions import IsAuthenticated

from datetime import datetime

# Doctor module views handle appointment access, prescription creation,
# and patient medical history retrieval for the assigned doctor.


class AppointmentViewset(viewsets.ModelViewSet):
    """Generic appointment endpoint for admin and doctor access."""

    permission_classes = [Roles('Admin', 'Doctor')]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer


class DoctorAppointmentsView(generics.ListAPIView):
    """List the appointments scheduled for a specific doctor today."""

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsSameDoctor]

    def get_queryset(self):
        """Return only the current day's appointments for the matched doctor."""
        return Appointment.objects.filter(
            doctor_id=self.kwargs["doctorid"],
            appointment_date=timezone.localdate()
        )


class PrescriptionView(APIView):
    """Create and read prescriptions tied to an appointment."""

    permission_classes = [IsAuthenticated]

    def post(self, request, doctorid, appointmentid):
        """Create a prescription only when the caller is the appointed doctor."""
        # Verify the logged-in user is the specified doctor.
        if (
            request.user.roleid.title.lower() != "doctor"
            or request.user.pk != doctorid
        ):
            return Response(
                {"error": "You are not authorized to write this prescription."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find the appointment belonging to this doctor.
        appointment = get_object_or_404(
            Appointment,
            pk=appointmentid,
            doctor_id=doctorid
        )

        # Prevent duplicate prescriptions.
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
        """Fetch the prescription for an appointment if it exists."""
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


class PatientTestReportsView(APIView):
    """Return lab results for a patient, optionally filtered by report date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, patientid):
        """Return a list of lab reports linked to the given patient."""
        date_str = request.query_params.get("date")

        results = LabResult.objects.filter(
            prescription_test__prescription__appointment__patient_id=patientid
        )
        if date_str:
            try:
                report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            results = results.filter(created_at__date=report_date)

        results = results.select_related(
            "prescription_test__test"
        ).order_by("-created_at")

        data = [
            {
                "test_name": result.prescription_test.test.test_name,
                "result_value": result.result_value,
                "unit": result.unit,
                "reference_range": result.reference_range,
                "remarks": result.remarks,
                "created_at": result.created_at,
            }
            for result in results
        ]

        return Response(data)


class PatientNotesLogView(APIView):
    """Return patient prescription notes and diagnosis summaries by date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, patientid):
        """Retrieve note history for a patient, optionally filtered to a day."""
        date_str = request.query_params.get("date")

        logs = Prescription.objects.filter(
            appointment__patient_id=patientid
        ).select_related("appointment", "appointment__doctor__doctor")

        if date_str:
            try:
                log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logs = logs.filter(created_on__date=log_date)

        logs = logs.order_by("-created_on")

        data = [
            {
                "doctor_name": note.appointment.doctor.doctor.full_name,
                "appointment_date": note.appointment.appointment_date,
                "symptoms": note.symptoms,
                "diagnosis": note.diagnosis,
                "notes": note.notes,
                "created_on": note.created_on,
            }
            for note in logs
        ]

        return Response(data)


class PatientMedicineLogView(APIView):
    """Return the medication history for a patient within a date range."""

    permission_classes = [IsAuthenticated]

    def get(self, request, patientid):
        """Return all prescriptions and prescribed medicine details in a time window."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"error": "Provide both start_date and end_date in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start > end:
            return Response(
                {"error": "start_date cannot be later than end_date."},
                status=status.HTTP_400_BAD_REQUEST
            )

        medicines = PrescriptionMedicine.objects.filter(
            prescription__appointment__patient_id=patientid,
            prescription__created_on__date__gte=start,
            prescription__created_on__date__lte=end
        ).select_related(
            "medicine",
            "prescription",
            "prescription__appointment"
        ).order_by("-prescription__created_on")

        data = [
            {
                "medicine_name": item.medicine.name,
                "category": item.medicine.category,
                "strength": item.medicine.strength,
                "quantity": item.quantity_alloted,
                "diagnosis": item.prescription.diagnosis,
                "prescription_date": item.prescription.created_on,
            }
            for item in medicines
        ]

        return Response(data)