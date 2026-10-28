from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from adminmodule.models import PrescriptionTest
from .models import LabResult
from .serializer import LabRequestSerializer, LabResultSerializer
from .permission import IsLabTechnician


class LabRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LabRequestSerializer
    permission_classes = [IsAuthenticated, IsLabTechnician]

    def get_queryset(self):
        queryset = PrescriptionTest.objects.select_related(
            "prescription__appointment__patient",
            "test"
        ).all()

        status = self.request.query_params.get("status")

        if status:
            queryset = queryset.filter(status__iexact=status)

        return queryset


class LabRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LabRequestSerializer
    permission_classes = [IsAuthenticated, IsLabTechnician]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = PrescriptionTest.objects.select_related(
            "prescription__appointment__patient",
            "test"
        ).all()

        status = self.request.query_params.get("status")

        if status:
            queryset = queryset.filter(status__iexact=status)

        return queryset

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
        return LabResult.objects.filter(
            technician=self.request.user
        ).select_related(
            "prescription_test",
            "technician"
        )

    def perform_create(self, serializer):
        serializer.save(technician=self.request.user)
