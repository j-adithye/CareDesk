from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adminmodule.models import Medicine, PrescriptionMedicine

from . import services
from .auth import Roles
from .serializers import AddStockSerializer, MedicineSerializer, PrescriptionLineSerializer


class MedicineViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    list / search, add, retrieve, disable (DELETE = soft delete) and add-stock.
    There is no update endpoint: the pharmacist cannot edit price or stock (FR-PHM-05).
    """

    serializer_class = MedicineSerializer
    lookup_value_regex = r"\d+"
    permission_classes = [IsAuthenticated, Roles("Pharmacist")]

    def get_queryset(self):
        qs = Medicine.objects.all().order_by("name")
        if self.action != "list":
            return qs
        params = self.request.query_params
        if params.get("include_inactive", "").lower() != "true":
            qs = qs.filter(is_active=True)  # FR-GEN-02
        term = params.get("search", "").strip()
        if term:
            cond = Q(name__icontains=term)
            if term.isdigit() and len(term) <= 9:
                cond |= Q(pk=int(term))  # FR-PHM-03: search by code or name
            qs = qs.filter(cond)
        return qs

    def perform_create(self, serializer):
        serializer.instance = services.add_medicine(self.request.user, **serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        services.disable_medicine(request.user, kwargs["pk"])
        return Response({"detail": "Medicine disabled."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add-stock", url_name="add-stock")
    def add_stock(self, request, pk=None):
        body = AddStockSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        medicine = services.add_stock(request.user, pk, body.validated_data["quantity"])
        return Response(MedicineSerializer(medicine).data, status=status.HTTP_200_OK)


class PrescriptionLineViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Issue Medicine screen: PENDING lines by default, plus the issue action."""

    serializer_class = PrescriptionLineSerializer
    lookup_value_regex = r"\d+"
    permission_classes = [IsAuthenticated, Roles("Pharmacist")]

    def get_queryset(self):
        qs = PrescriptionMedicine.objects.select_related(
            "medicine",
            "prescription__appointment__patient",
            "prescription__appointment__doctor__doctor",
        ).order_by("id")
        if self.action != "list":
            return qs
        wanted = self.request.query_params.get("status", services.PENDING).upper()
        if wanted in (services.PENDING, services.ISSUED):
            qs = qs.filter(status=wanted)
        return qs

    @action(detail=True, methods=["post"], url_path="issue", url_name="issue")
    def issue(self, request, pk=None):
        line = services.issue_line(request.user, pk)
        line = self.get_queryset().get(pk=line.pk)
        return Response(self.get_serializer(line).data, status=status.HTTP_200_OK)
