from decimal import Decimal

from rest_framework import serializers

from adminmodule.models import Medicine, PrescriptionMedicine


# Pharmacist serializers for medicine catalog actions and prescription-line review.
# They validate input values and format the response payloads used by the UI.


class MedicineSerializer(serializers.ModelSerializer):
    """Validate medicine creation payloads and expose inventory details."""

    name = serializers.CharField(
        max_length=100,
        min_length=3,
        error_messages={"min_length": "Medicine name must be at least 3 characters."},
    )
    generic_name = serializers.CharField(max_length=100)
    company_name = serializers.CharField(max_length=100)
    unit_price = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        error_messages={"min_value": "Price must be greater than 0."},
    )

    class Meta:
        model = Medicine
        fields = ["id", "name", "generic_name", "company_name", "stock_left", "unit_price", "is_active"]
        read_only_fields = ["id", "stock_left", "is_active"]


class AddStockSerializer(serializers.Serializer):
    """Validate the quantity added to an existing medicine stock record."""

    quantity = serializers.IntegerField(
        min_value=1,
        max_value=1_000_000,
        error_messages={
            "min_value": "Quantity must be a whole number greater than zero.",
            "invalid": "Quantity must be a whole number greater than zero.",
        },
    )


class PrescriptionLineSerializer(serializers.ModelSerializer):
    """Expose a prescription medicine line to the pharmacist issue workflow."""

    prescription_id = serializers.IntegerField(read_only=True)
    patient_name = serializers.CharField(source="prescription.appointment.patient.full_name", read_only=True)
    doctor_name = serializers.CharField(source="prescription.appointment.doctor.doctor.full_name", read_only=True)
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    quantity_required = serializers.IntegerField(source="quantity_alloted", read_only=True)
    current_stock = serializers.IntegerField(source="medicine.stock_left", read_only=True)

    class Meta:
        model = PrescriptionMedicine
        fields = [
            "id", "prescription_id", "patient_name", "doctor_name",
            "medicine_id", "medicine_name", "quantity_required", "current_stock",
            "unit_price", "total", "status",
        ]
        read_only_fields = fields
