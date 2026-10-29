from rest_framework import serializers
from adminmodule.models import Appointment, Prescription, PrescriptionMedicine, PrescriptionTest, Medicine, Test
from django.db import transaction

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
        
        
class PrescriptionMedicineSerializer(serializers.ModelSerializer):
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.filter(is_active=True),
        source="medicine",
        write_only=True
    )

    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )

    class Meta:
        model = PrescriptionMedicine
        fields = [
            "medicine_id",
            "medicine_name",
            "quantity_alloted",
            "unit_price",
            "total",
            "status",
        ]
        read_only_fields = ["unit_price", "total"]


class PrescriptionTestSerializer(serializers.ModelSerializer):
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
    medicines = PrescriptionMedicineSerializer(many=True, required=False)
    tests = PrescriptionTestSerializer(many=True, required=False)

    class Meta:
        model = Prescription
        fields = [
            "appointment",
            "symptoms",
            "diagnosis",
            "created_on",
            "medicines",
            "tests",
        ]
        read_only_fields = ["appointment", "created_on"]

    @transaction.atomic
    def create(self, validated_data):
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
        