
from rest_framework import serializers
from adminmodule.models import PrescriptionTest
from .models import LabResult

# Serializers for lab requests and lab result submissions.
# They expose request details and ensure result values are not blank.


class LabRequestSerializer(serializers.ModelSerializer):
    """Expose prescription test requests as lab work items."""

    patient_name = serializers.CharField(
        source="prescription.appointment.patient.full_name",
        read_only=True
    )

    test_name = serializers.CharField(
        source="test.test_name",
        read_only=True
    )

    class Meta:
        model = PrescriptionTest
        fields = [
            "prescription",
            "test",
            "patient_name",
            "test_name",
            "quantity_alloted",
            "unit_price",
            "total",
            "status",
        ]
        read_only_fields = [
            "prescription",
            "test",
            "patient_name",
            "quantity_alloted",
            "unit_price",
            "total",
        ]


class LabResultSerializer(serializers.ModelSerializer):
    """Validate and serialize lab result submissions from technicians."""

    technician_name = serializers.CharField(
        source="technician.full_name",
        read_only=True
    )
    test_name = serializers.CharField(
        source="prescription_test.test.test_name",
        read_only=True
    )

    class Meta:
        model = LabResult
        fields = [
            "id",
            "test_name",
            "technician",
            "technician_name",
            "result_value",
            "unit",
            "reference_range",
            "remarks",
        ]
        read_only_fields = [
            "id",
            "technician",
            "technician_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        """Reject empty lab result values before saving."""
        result_value = attrs.get(
            "result_value",
            getattr(self.instance, "result_value", "")
        )

        if not result_value.strip():
            raise serializers.ValidationError({
                "result_value": "A result value is required."
            })

        return attrs
