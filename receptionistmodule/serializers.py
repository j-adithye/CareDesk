import re                                           # regular expressions, for pattern checks
from datetime import date                           # lets us get today's date
from rest_framework import serializers              # DRF's serializer tools
from adminmodule.models import Patient              # the shared Patient model (we don't make our own)

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