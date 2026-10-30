import re
from datetime import date
from rest_framework import serializers
from adminmodule.models import Appointment, DoctorDetails, Patient, Billing

# Receptionist validation layer for patient registration, doctor lookup,
# appointment booking, and billing-related responses.

GENDERS = {"F", "M", "O"}
BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


def check_phone(value):
    """Validate phone numbers as exactly 10 digits."""
    if not re.fullmatch(r"[0-9]{10}", value):
        raise serializers.ValidationError("Phone must be exactly 10 digits.")
    return value


class PatientSerializer(serializers.ModelSerializer):
    """Serializer used when a receptionist registers a new patient."""

    full_name = serializers.CharField(
        max_length=50, min_length=3,
        error_messages={"min_length": "Name must be at least 3 characters."},
    )
    blood_group = serializers.CharField(max_length=3)
    address = serializers.CharField(max_length=100)

    class Meta:
        model = Patient
        fields = ["id", "full_name", "dob", "gender", "blood_group",
                "phone", "address", "created_on", "is_active"]
        read_only_fields = ["id", "created_on", "is_active"]

    def validate_full_name(self, value):
        """Allow only letters and spaces in patient names."""
        if not value.replace(" ", "").isalpha():
            raise serializers.ValidationError("Name can contain only letters and spaces.")
        return value

    def validate_dob(self, value):
        """Reject birth dates in the future."""
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_gender(self, value):
        """Restrict gender to the allowed codes used by the clinic."""
        if value not in GENDERS:
            raise serializers.ValidationError("Gender must be F, M or O.")
        return value

    def validate_blood_group(self, value):
        """Require a valid blood group from the supported set."""
        if value not in BLOOD_GROUPS:
            raise serializers.ValidationError(f"Blood group must be one of {sorted(BLOOD_GROUPS)}.")
        return value

    def validate_phone(self, value):
        """Reuse the general phone validation helper."""
        return check_phone(value)


class PatientEditSerializer(serializers.ModelSerializer):
    """Serializer for patching patient phone and address details."""

    address = serializers.CharField(max_length=100)

    class Meta:
        model = Patient
        fields = ["phone", "address"]

    def validate_phone(self, value):
        """Validate changed phone values before saving."""
        return check_phone(value)

    def validate(self, data):
        """Reject any unsupported edit fields in a patch request."""
        extra = set(self.initial_data) - {"phone", "address"}
        if extra:
            raise serializers.ValidationError("Only phone and address can be edited.")
        return data


class DoctorSerializer(serializers.ModelSerializer):
    """Read-only doctor profile for the receptionist booking flow."""

    id = serializers.IntegerField(source="pk", read_only=True)
    full_name = serializers.CharField(source="doctor.full_name", read_only=True)
    weekdays = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = DoctorDetails
        fields = ["id", "full_name", "specialization", "consultation_fees",
                "weekdays", "start_time", "end_time"]
        read_only_fields = fields


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for booking and returning appointment records."""

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "doctor",
            "appointment_date",
            "appointment_time",
            "reason",
            "created_on",
        ]
        read_only_fields = ["id", "created_on"]

    def validate_patient(self, value):
        """Ensure the patient exists and is active before scheduling an appointment."""
        if not Patient.objects.filter(pk=value.pk, is_active=True).exists():
            raise serializers.ValidationError("Patient does not exist or is disabled.")
        return value

    def validate_doctor(self, value):
        """Ensure the selected doctor exists and is active."""
        if not DoctorDetails.objects.filter(pk=value.pk, doctor__is_active=True).exists():
            raise serializers.ValidationError("Doctor does not exist or is inactive.")
        return value

    def validate_appointment_date(self, value):
        """Reject appointment dates in the past."""
        if value < date.today():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value


class BillingSerializer(serializers.ModelSerializer):
    """Format a billing record for the receptionist billing API."""

    patient_name = serializers.CharField(
        source="prescription.appointment.patient.full_name",
        read_only=True
    )

    appointment_id = serializers.IntegerField(
        source="prescription.appointment.id",
        read_only=True
    )

    consultation_fees = serializers.DecimalField(
        source="prescription.appointment.doctor.consultation_fees",
        read_only=True,
        max_digits=8, decimal_places=2
    )

    class Meta:
        model = Billing
        fields = [
            "prescription",
            "appointment_id",
            "patient_name",
            "consultation_fees",
            "sub_total",
            "taxes",
            "grand_total",
            "created_on",
            "paid_on",
        ]
