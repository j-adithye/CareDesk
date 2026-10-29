from django.db.models import Q                      # Q lets us build "this OR that" database filters
from rest_framework import mixins, status, viewsets   # mixins = ready-made behaviours; status = HTTP codes
from rest_framework.decorators import action        # for our own extra endpoint
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated   # "must be logged in"
from rest_framework.response import Response        # builds the JSON response

from adminmodule.models import Patient
from . import services                              # our business rules (. = this folder)
from .permissions import IsReceptionist             # our role rule from section 3
from .serializers import DoctorSerializer, PatientEditSerializer, PatientSerializer


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