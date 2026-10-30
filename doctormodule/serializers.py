from rest_framework import serializers
from .models import Appointment, Prescription, PrescriptionMedicine, PrescriptionTest, Medicine, Test
from django.db import transaction

# Doctor-facing serializers for appointment and prescription payloads.
# These serializers clean incoming data and keep medicine/test totals consistent.


class AppointmentSerializer(serializers.ModelSerializer):
    """Serialize appointment data for doctor workflows."""

    class Meta:
        model = Appointment
        fields = '__all__'


class PrescriptionMedicineSerializer(serializers.ModelSerializer):
    """Serializer for medicine lines inside a prescription."""

    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.filter(is_active=True),
        source="medicine",
        write_only=True
    )

    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )

    strength = serializers.CharField(source="medicine.strength", read_only=True)
    category = serializers.CharField(source="medicine.category", read_only=True)

    class Meta:
        model = PrescriptionMedicine
        fields = [
            "medicine_id",
            "medicine_name",
            "strength",
            "category",
            "quantity_alloted",
            "unit_price",
            "total",
            "status",
        ]
        read_only_fields = ["unit_price", "total"]


class PrescriptionTestSerializer(serializers.ModelSerializer):
    """Serializer for laboratory test lines inside a prescription."""

    test_id = serializers.PrimaryKeyRelatedField(
        queryset=Test.objects.filter(is_active=True),
        source="test",
        write_only=True
    )

    test_name = serializers.CharField(
        source="test.test_name",
        read_only=True
    )

    class Meta:
        model = PrescriptionTest
        fields = [
            "test_id",
            "test_name",
            "quantity_alloted",
            "unit_price",
            "total",
            "status",
        ]
        read_only_fields = ["unit_price", "total"]


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serialize a prescription with nested medicine and test entries."""

    medicines = PrescriptionMedicineSerializer(many=True, required=False)
    tests = PrescriptionTestSerializer(many=True, required=False)

    class Meta:
        model = Prescription
        fields = [
            "appointment",
            "symptoms",
            "diagnosis",
            "notes",
            "created_on",
            "medicines",
            "tests",
        ]
        read_only_fields = ["appointment", "created_on"]

    @transaction.atomic
    def create(self, validated_data):
        """Create the prescription and nested medicine/test lines in one transaction."""
        medicines_data = validated_data.pop("medicines", [])
        tests_data = validated_data.pop("tests", [])

        prescription = Prescription.objects.create(**validated_data)

        for item in medicines_data:
            medicine = item.pop("medicine")
            quantity = item.pop("quantity_alloted")
            price = medicine.unit_price

            PrescriptionMedicine.objects.create(
                prescription=prescription,
                medicine=medicine,
                quantity_alloted=quantity,
                unit_price=price,
                total=quantity * price,
                **item
            )

        for item in tests_data:
            test = item.pop("test")
            quantity = item.pop("quantity_alloted")
            price = test.unit_price

            PrescriptionTest.objects.create(
                prescription=prescription,
                test=test,
                quantity_alloted=quantity,
                unit_price=price,
                total=quantity * price,
                **item
            )

        return prescription
