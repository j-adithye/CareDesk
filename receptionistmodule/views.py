from django.db.models import Q
from rest_framework import mixins, status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adminmodule.models import Patient, Appointment, DoctorDetails, Billing
from . import services
from .services import (
    book_appointment,
    generate_consultation_bill,
)
from .permissions import IsReceptionist
from .serializers import (
    DoctorSerializer,
    PatientEditSerializer,
    PatientSerializer,
    AppointmentSerializer,
    BillingSerializer,
)

# Receptionist endpoints for patients, doctors, appointments, and bill generation.
# The view layer keeps HTTP concerns separate from the service validation layer.


class PatientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Manage patient records for registration, lookup, and soft disable actions."""

    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        """Return active patients by default and allow search across registration number and phone."""
        qs = Patient.objects.all().order_by("id")

        if self.action != "list":
            return qs

        params = self.request.query_params
        if params.get("include_inactive", "").lower() != "true":
            qs = qs.filter(is_active=True)

        term = params.get("search", "").strip()
        if term:
            cond = Q(phone=term)
            if term.isdigit() and len(term) <= 9:
                cond |= Q(pk=int(term))
            qs = qs.filter(cond)
        return qs

    def list(self, request, *args, **kwargs):
        """Return patients with a friendly empty-result message when the search has no match."""
        patients = self.get_queryset()
        message = ""
        if request.query_params.get("search") and not patients.exists():
            message = "Sorry, there is no such patient."
        return Response({
            "message": message,
            "results": self.get_serializer(patients, many=True).data,
        })

    def create(self, request, *args, **kwargs):
        """Create a patient through the receptionist service and return a clear response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = services.register_patient(request.user, **serializer.validated_data)
        return Response(
            {
                "message": "Successfully added",
                "registration_number": patient.pk,
                "patient": self.get_serializer(patient).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        """Allow PATCH updates only for phone and address on an existing patient."""
        serializer = PatientEditSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            raise ValidationError({"detail": "Send phone and/or address."})
        patient = services.edit_patient(request.user, pk, **serializer.validated_data)
        return Response(self.get_serializer(patient).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        """Soft-disable a patient record after validation checks pass."""
        services.disable_patient(request.user, pk)
        return Response({"detail": "Patient disabled."})


class DoctorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only doctor directory used by the receptionist appointment flow."""

    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        """Return active doctors and support searching by name or specialization."""
        qs = (
            DoctorDetails.objects
            .select_related("doctor")
            .prefetch_related("weekdays")
            .filter(doctor__is_active=True)
            .order_by("doctor__full_name")
        )
        term = self.request.query_params.get("search", "").strip()
        if term:
            qs = qs.filter(Q(doctor__full_name__icontains=term) | Q(specialization__icontains=term))
        return qs

    def list(self, request, *args, **kwargs):
        """Return doctor results with a friendly empty-search message when needed."""
        doctors = self.get_queryset()
        message = ""
        if request.query_params.get("search") and not doctors.exists():
            message = "Sorry, there is no such doctor."
        return Response({"message": message,
                        "results": self.get_serializer(doctors, many=True).data})


class AppointmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Booking and viewing endpoints for receptionists."""

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    lookup_value_regex = r"\d+"


class BillingListView(generics.ListAPIView):
    """List all generated bills for the receptionist module."""

    queryset = Billing.objects.select_related(
        "prescription__appointment__patient",
        "prescription__appointment__doctor"
    ).order_by("-created_on")

    serializer_class = BillingSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]

    def create(self, request, *args, **kwargs):
        """Handle POST requests to create new appointments via the service layer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = book_appointment(
            request.user,
            patient_id=serializer.validated_data["patient"].pk,
            doctor_id=serializer.validated_data["doctor"].pk,
            appointment_date=serializer.validated_data["appointment_date"],
            appointment_time=serializer.validated_data["appointment_time"],
            reason=serializer.validated_data["reason"],
        )

        return Response(
            {
                "message": "Appointment booked successfully.",
                "appointment_id": appointment.pk,
                "patient_token": appointment.pk,
                "appointment": self.get_serializer(appointment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="generate-bill")
    def generate_bill(self, request, pk=None):
        """Generate the consultation bill for a specific appointment."""
        bill = generate_consultation_bill(request.user, pk)

        return Response(
            {
                "message": "Consultation bill generated successfully.",
                "appointment_id": int(pk),
                "bill_id": bill.pk,
                "grand_total": str(bill.grand_total),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        """Allow rescheduling only when no prescription exists and the time window permits it."""
        from datetime import datetime, timedelta
        from django.utils import timezone
        from rest_framework.exceptions import ValidationError
        from adminmodule.models import Appointment, Prescription

        appointment = self.get_object()

        appointment_datetime = timezone.make_aware(
            datetime.combine(
                appointment.appointment_date,
                appointment.appointment_time
            )
        )

        if timezone.now() > appointment_datetime - timedelta(hours=2):
            raise ValidationError({
                "detail": "Rescheduling is allowed only at least 2 hours before the appointment."
            })

        if Prescription.objects.filter(appointment=appointment).exists():
            raise ValidationError({
                "detail": "An appointment with a prescription cannot be rescheduled."
            })

        serializer = self.get_serializer(
            appointment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Appointment rescheduled successfully.",
                "appointment": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"], url_path="bill")
    def view_bill(self, request, pk=None):
        """Return the bill linked to a selected appointment."""
        appointment = self.get_object()

        try:
            bill = Billing.objects.select_related(
                "prescription__appointment__patient"
            ).get(prescription__appointment=appointment)

        except Billing.DoesNotExist:
            return Response(
                {"detail": "No bill found for this appointment."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BillingSerializer(bill)
        return Response(serializer.data)
