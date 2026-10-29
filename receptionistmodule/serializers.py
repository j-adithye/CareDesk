import re                                           # regular expressions, for pattern checks
from datetime import date                           # lets us get today's date
from rest_framework import serializers              # DRF's serializer tools
from adminmodule.models import Appointment,DoctorDetails,Patient              # the shared Patient model (we don't make our own)

GENDERS = {"F", "M", "O"}                           # allowed genders, from the document (a set = fast lookup)
BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}   # the 8 valid blood groups


def check_phone(value):                             # shared helper used by both serializers
    if not re.fullmatch(r"[0-9]{10}", value):       # whole text must be exactly 10 characters, each 0-9
        raise serializers.ValidationError("Phone must be exactly 10 digits.")   # becomes a 400 response
    return value                                    # valid, so hand the value back


class PatientSerializer(serializers.ModelSerializer):   # builds fields from the Patient model
    full_name = serializers.CharField(
        max_length=50, min_length=3,                # the document says 3 to 50 characters
        error_messages={"min_length": "Name must be at least 3 characters."},   # friendly message
    )
    blood_group = serializers.CharField(max_length=3)   # re-declared so it is REQUIRED (the model allows blank)
    address = serializers.CharField(max_length=100)     # required, at most 100 characters

    class Meta:                                     # settings for this serializer
        model = Patient                             # which model it works with
        fields = ["id", "full_name", "dob", "gender", "blood_group",
                "phone", "address", "created_on", "is_active"]   # fields shown in the JSON
        read_only_fields = ["id", "created_on", "is_active"]
        # Visible in responses but ignored if sent in a request:
        # id = registration number (database makes it), is_active = changed only by "disable"

    def validate_full_name(self, value):            # DRF calls validate_<field> automatically
        if not value.replace(" ", "").isalpha():    # remove spaces, then every character must be a letter
            raise serializers.ValidationError("Name can contain only letters and spaces.")
        return value

    def validate_dob(self, value):
        if value > date.today():                    # a date after today is in the future
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_gender(self, value):
        if value not in GENDERS:                    # must be F, M or O
            raise serializers.ValidationError("Gender must be F, M or O.")
        return value

    def validate_blood_group(self, value):
        if value not in BLOOD_GROUPS:               # must be one of the 8 groups
            raise serializers.ValidationError(f"Blood group must be one of {sorted(BLOOD_GROUPS)}.")
        return value

    def validate_phone(self, value):
        return check_phone(value)                   # reuse the helper above


class PatientEditSerializer(serializers.ModelSerializer):   # used only for PATCH (edit)
    address = serializers.CharField(max_length=100)

    class Meta:
        model = Patient
        fields = ["phone", "address"]               # only these two fields exist in this serializer

    def validate_phone(self, value):
        return check_phone(value)

    def validate(self, data):                       # runs after the field checks, sees the whole request
        extra = set(self.initial_data) - {"phone", "address"}
        # self.initial_data = the raw JSON sent. set(...) = its keys.
        # Subtracting {"phone","address"} leaves any OTHER keys, like "full_name"
        if extra:
            raise serializers.ValidationError("Only phone and address can be edited.")
        return data
class DoctorSerializer(serializers.ModelSerializer):
    """Read-only view of a doctor for the receptionist (used when booking)."""

    # DoctorDetails uses the Staff id as its primary key, so pk is the doctor's id.
    id = serializers.IntegerField(source="pk", read_only=True)

    # "doctor" points to the Staff row; the doctor's name lives there.
    full_name = serializers.CharField(source="doctor.full_name", read_only=True)

    # weekdays is a many-to-many link. This shows each weekday as its name
    # (for example ["Monday", "Wednesday"]) instead of a list of ids.
    weekdays = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = DoctorDetails
        fields = ["id", "full_name", "specialization", "consultation_fees",
                "weekdays", "start_time", "end_time"]
        read_only_fields = fields      # nothing here can be changed by the receptionist

class AppointmentSerializer(serializers.ModelSerializer):  # Creates a serializer using the existing Appointment model.

    class Meta:  # Defines the serializer's model and fields.
        model = Appointment  # Uses the existing Appointment table.
        fields = [  # Lists the appointment fields accepted or returned by the API.
            "id",  # The existing appointment ID, which also serves as the patient token.
            "patient",  # The ID of the patient being booked.
            "doctor",  # The ID of the selected doctor.
            "appointment_date",  # The requested appointment date.
            "appointment_time",  # The requested appointment time.
            "reason",  # The reason for the appointment.
            "created_on",  # The timestamp when the appointment was created.
        ]
        read_only_fields = ["id", "created_on"]  # Prevents clients from choosing the ID or creation timestamp.

    def validate_patient(self, value):  # Validates the selected patient before booking.
        if not Patient.objects.filter(pk=value.pk, is_active=True).exists():  # Checks that the patient exists and is active.
            raise serializers.ValidationError("Patient does not exist or is disabled.")  # Rejects invalid or disabled patients.
        return value  # Returns the validated patient.

    def validate_doctor(self, value):  # Validates the selected doctor before booking.
        if not DoctorDetails.objects.filter(pk=value.pk, doctor__is_active=True).exists():  # Checks that the doctor is active.
            raise serializers.ValidationError("Doctor does not exist or is inactive.")  # Rejects an invalid or inactive doctor.
        return value  # Returns the validated doctor.

    def validate_appointment_date(self, value):  # Validates the requested appointment date.
        if value < date.today():  # Checks whether the requested date is before today.
            raise serializers.ValidationError("Appointment date cannot be in the past.")  # Rejects past dates.
        return value  # Returns the validated date.