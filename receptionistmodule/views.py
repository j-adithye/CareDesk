from django.db.models import Q                      # Q lets us build "this OR that" database filters
from rest_framework import mixins, status, viewsets   # mixins = ready-made behaviours; status = HTTP codes
from rest_framework.decorators import action        # for our own extra endpoint
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated   # "must be logged in"
from rest_framework.response import Response        # builds the JSON response
from rest_framework import generics

from adminmodule.models import Patient, Appointment,DoctorDetails,Billing
from . import services
from .services import (
    book_appointment,             # Imports the appointment-booking service.
    generate_consultation_bill,   # Imports the consultation-billing service.
)                                  # our business rules (. = this folder)
from .permissions import IsReceptionist   # our role rule from section 3
from .serializers import (
        DoctorSerializer, 
        PatientEditSerializer, 
        PatientSerializer,
        AppointmentSerializer,
        BillingSerializer,
        )

class PatientViewSet(
    mixins.ListModelMixin,       # adds GET  /patients/
    mixins.RetrieveModelMixin,   # adds GET  /patients/<id>/
    mixins.CreateModelMixin,     # adds POST /patients/
    viewsets.GenericViewSet,     # the base class that holds them together
):
    # We chose only these mixins on purpose: no delete and no full update exist at all

    serializer_class = PatientSerializer            # the default serializer for this view
    permission_classes = [IsAuthenticated, IsReceptionist]
    # Both must pass, in order: valid token (else 401), then Receptionist role (else 403)

    lookup_value_regex = r"\d+"                     # the <id> in the URL must be digits only

    def get_queryset(self):                         # decides WHICH patients this view can see
        qs = Patient.objects.all().order_by("id")   # start with all patients, oldest first

        if self.action != "list":                   # for single-patient URLs, no filtering
            return qs

        params = self.request.query_params          # the ?key=value part of the URL

        if params.get("include_inactive", "").lower() != "true":
            qs = qs.filter(is_active=True)          # hide disabled patients unless asked (FR-GEN-02)

        term = params.get("search", "").strip()     # text typed after ?search=
        if term:
            cond = Q(phone=term)                    # match phone exactly...
            if term.isdigit() and len(term) <= 9:   # ...and if it is a short number...
                cond |= Q(pk=int(term))             # ...OR match the registration number (|= means "or also")
            qs = qs.filter(cond)
        return qs

    def list(self, request, *args, **kwargs):       # replaces the default GET /patients/
        patients = self.get_queryset()
        message = ""
        if request.query_params.get("search") and not patients.exists():
            message = "Sorry, there is no such patient."    # exact wording from FR-PAT-05
        return Response({
            "message": message,
            "results": self.get_serializer(patients, many=True).data,   # many=True = a list of patients
        })

    def create(self, request, *args, **kwargs):     # replaces the default POST /patients/
        serializer = self.get_serializer(data=request.data)   # load the JSON body into the serializer
        serializer.is_valid(raise_exception=True)             # format problems stop here with a 400
        patient = services.register_patient(request.user, **serializer.validated_data)
        # ** turns the checked dict into named arguments; the service does the real work
        return Response(
            {
                "message": "Successfully added",              # FR-PAT-04
                "registration_number": patient.pk,
                "patient": self.get_serializer(patient).data,
            },
            status=status.HTTP_201_CREATED,                   # 201 = "created"
        )

    def partial_update(self, request, pk=None):     # PATCH /patients/<id>/ ; pk is the id from the URL
        serializer = PatientEditSerializer(data=request.data, partial=True)
        # partial=True: the receptionist may send only phone, only address, or both
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:           # empty body: nothing to change
            raise ValidationError({"detail": "Send phone and/or address."})
        patient = services.edit_patient(request.user, pk, **serializer.validated_data)
        return Response(self.get_serializer(patient).data)

    @action(detail=True, methods=["post"])          # our own endpoint on ONE patient, POST only
    def disable(self, request, pk=None):            # URL becomes /patients/<id>/disable/ (named after the function)
        services.disable_patient(request.user, pk)  # the service checks the rules and does it
        
        return Response({"detail": "Patient disabled."})

class DoctorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    # Read-only: only list and retrieve exist, so there is no way to add or edit a doctor here.
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        qs = (
            DoctorDetails.objects
            .select_related("doctor")          # loads the Staff row in the same query
            .prefetch_related("weekdays")      # loads all weekdays in one extra query
            .filter(doctor__is_active=True)    # FR-APT-02: only active doctors are shown
            .order_by("doctor__full_name")
        )
        term = self.request.query_params.get("search", "").strip()
        if term:
            # ?search= matches the doctor's name OR specialization
            qs = qs.filter(Q(doctor__full_name__icontains=term) | Q(specialization__icontains=term))
        return qs

    def list(self, request, *args, **kwargs):
        doctors = self.get_queryset()
        message = ""
        if request.query_params.get("search") and not doctors.exists():
            message = "Sorry, there is no such doctor."
        # Same response shape as the patients list, so the frontend handles both alike
        return Response({"message": message,
                        "results": self.get_serializer(doctors, many=True).data})
class AppointmentViewSet(  # Defines the API endpoints for receptionist appointments.
    mixins.ListModelMixin,  # Enables GET requests to list appointments.
    mixins.RetrieveModelMixin,  # Enables GET requests to retrieve one appointment.
    mixins.CreateModelMixin,  # Enables POST requests to create appointments.
    viewsets.GenericViewSet,  # Provides the common functionality for these API actions.
):
    serializer_class = AppointmentSerializer  # Uses the existing serializer to validate and represent appointments.
    permission_classes = [IsAuthenticated, IsReceptionist]  # Requires an authenticated user with receptionist permission.
    lookup_value_regex = r"\d+"  # Restricts appointment URL identifiers to numeric IDs.
class BillingListView(generics.ListAPIView):
    queryset = Billing.objects.select_related(
        "prescription__appointment__patient",
        "prescription__appointment__doctor"
    ).order_by("-created_on")

    serializer_class = BillingSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]  # Sorts appointments chronologically.

    def create(self, request, *args, **kwargs): # Handle POST requests to create a new appointment.
        serializer = self.get_serializer(data=request.data)# Validate the patient, doctor, date, time, and other submitted fields.
        serializer.is_valid(raise_exception=True)# Raise a 400 Bad Request response if validation fails.
        appointment = book_appointment(
            request.user,  # Passes the currently authenticated receptionist.
            patient_id=serializer.validated_data["patient"].pk,  # Extracts the patient's database ID.
            doctor_id=serializer.validated_data["doctor"].pk,  # Extracts the doctor's database ID.
            appointment_date=serializer.validated_data["appointment_date"],  # Passes the requested appointment date.
            appointment_time=serializer.validated_data["appointment_time"],  # Passes the requested appointment time.
            reason=serializer.validated_data["reason"],  # Passes the consultation reason.
        )

        return Response(
            {
                "message": "Appointment booked successfully.",# Confirm that the appointment was created.
                "appointment_id": appointment.pk,# Return the appointment's database ID.
                "patient_token": appointment.pk,# Use the same appointment ID as the patient token, as you requested.
                "appointment": self.get_serializer(appointment).data,# Return the saved appointment details.
            },

            status=status.HTTP_201_CREATED,# Return HTTP 201 Created after successful booking.
        )

    @action(detail=True, methods=["post"], url_path="generate-bill")# Creates a POST endpoint for generating a bill for one appointment.

    def generate_bill(self, request, pk=None):
        # Handles requests to generate a consultation bill.

        bill = generate_consultation_bill(request.user, pk)
        # Calls the billing service using the logged-in receptionist and appointment ID.

        return Response(
            {
                "message": "Consultation bill generated successfully.",
                # Confirms that the bill was generated.

                "appointment_id": int(pk),
                # Returns the appointment ID, which is also the patient token.

                "bill_id": bill.pk,
                # Returns the unique database ID of the bill.

                "grand_total": str(bill.grand_total),
                # Returns the final amount as a string to preserve decimal precision.
            },
            status=status.HTTP_201_CREATED,# Returns HTTP 201 to indicate successful bill creation.
        )
    @action(detail=True, methods=["patch"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        from datetime import datetime, timedelta
        from django.utils import timezone
        from rest_framework.exceptions import ValidationError
        from adminmodule.models import Appointment, Prescription

        appointment = self.get_object()

        # Allow rescheduling only at least 2 hours before the appointment.
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

        # Do not allow rescheduling after a prescription has been created.
        if Prescription.objects.filter(appointment=appointment).exists():
            raise ValidationError({
                "detail": "An appointment with a prescription cannot be rescheduled."
            })

        # Validate the new appointment details.
        serializer = self.get_serializer(
            appointment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        # Save the new appointment details.
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
        # Get the selected appointment.
        appointment = self.get_object()

        try:
            # Find the bill associated with this appointment.
            bill = Billing.objects.select_related(
                "prescription__appointment__patient"
            ).get(prescription__appointment=appointment)

        except Billing.DoesNotExist:
            # Return an error if no bill exists.
            return Response(
                {"detail": "No bill found for this appointment."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert the bill into JSON.
        serializer = BillingSerializer(bill)

        # Return the bill details.
        return Response(serializer.data)