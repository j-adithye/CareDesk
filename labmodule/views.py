from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from adminmodule.models import PrescriptionTest
from .models import LabResult
from .serializer import LabRequestSerializer, LabResultSerializer
from .permission import IsLabTechnician

from datetime import date
from django.utils import timezone

class LabRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LabRequestSerializer
    permission_classes = [IsAuthenticated, IsLabTechnician]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        date_str = self.request.query_params.get("date")

        if date_str:
            try:
                selected_date = date.fromisoformat(date_str)
            except ValueError:
                raise ValidationError({"date": "Use YYYY-MM-DD format."})
        else:
            selected_date = timezone.localdate()

        queryset = PrescriptionTest.objects.select_related(
            "prescription__appointment__patient",
            "test"
        )

        queryset = queryset.filter(
            prescription__appointment__appointment_date=selected_date
        )

    @action(detail=True, methods=["patch"], url_path="issue")
    def issue(self, request, pk=None):
        test = self.get_object()

        if test.status != "PENDING":
            raise ValidationError("Only pending tests can be issued.")

        test.status = "ISSUED"
        test.save(update_fields=["status"])

        return Response({
            "message": "Test issued successfully.",
            "prescription_test_id": test.pk,
            "status": test.status
        }, status=status.HTTP_200_OK)
    
class LabRequestStatusViewSet(viewsets.ModelViewSet):
    serializer_class = LabRequestSerializer
    permission_classes = [IsAuthenticated, IsLabTechnician]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return PrescriptionTest.objects.select_related(
            "prescription__appointment__patient",
            "test"
        ).all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if not partial:
            raise ValidationError(
                "Use PATCH to update the test status."
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return_response = serializer.data

        from rest_framework.response import Response
        return Response(return_response)


class LabResultViewSet(viewsets.ModelViewSet):
    serializer_class = LabResultSerializer
    permission_classes = [IsAuthenticated, IsLabTechnician]
    http_method_names = [
        "get", "post", "patch", "head", "options"
    ]


    def get_queryset(self):
        queryset = LabResult.objects.filter(
            technician=self.request.user
        ).select_related(
            "prescription_test__test",
            "prescription_test__prescription__appointment__patient",
            "technician",
        )

        # Search results by patient ID
        patient_id = self.request.query_params.get("patientid")

        if patient_id:
            if not patient_id.isdigit():
                raise ValidationError({
                    "patientid": "Patient ID must be a number."
                })

            queryset = queryset.filter(
                prescription_test__prescription__appointment__patient_id=patient_id
            )

        # Filter results by creation date (optional)
        date_str = self.request.query_params.get("date")

        if date_str:
            queryset = queryset.filter(created_at__date=date_str)

        return queryset.order_by("-created_at")


    def perform_create(self, serializer):
        serializer.save(technician=self.request.user)
