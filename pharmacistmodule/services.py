"""Pharmacist business rules (FR-PHM-01..10). Views only call these functions."""
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from adminmodule.models import ActivityLog, Medicine, PrescriptionMedicine

from .auth import has_role

PENDING = "PENDING"
ISSUED = "ISSUED"


def _require_pharmacist(user):
    # Second authorisation check in the service layer (NFR-SEC-04).
    if not has_role(user, "Pharmacist"):
        raise PermissionDenied("Not allowed. Required role: Pharmacist.")


def _log(staff, action, details):
    # Called after the business action succeeded, never with secrets (FR-LOG-02/03).
    ActivityLog.objects.create(staff=staff, message=f"{action} {details}"[:255])


def _locked_medicine(pk):
    try:
        return Medicine.objects.select_for_update().get(pk=pk)
    except Medicine.DoesNotExist:
        raise NotFound("Medicine not found.")


def add_medicine(user, *, name, generic_name, company_name, unit_price):
    """FR-PHM-01/02: stock starts at 0; duplicate name + company is rejected."""
    _require_pharmacist(user)
    with transaction.atomic():
        if Medicine.objects.filter(name__iexact=name, company_name__iexact=company_name).exists():
            raise ValidationError(
                {"name": ["A medicine with this name and company already exists."]}
            )
        medicine = Medicine.objects.create(
            name=name,
            generic_name=generic_name,
            company_name=company_name,
            unit_price=unit_price,
            stock_left=0,
            is_active=True,
        )
        _log(user, "MEDICINE_ADD", f"id={medicine.pk} name={medicine.name} company={medicine.company_name}")
    return medicine


def disable_medicine(user, pk):
    """FR-PHM-04: soft delete."""
    _require_pharmacist(user)
    with transaction.atomic():
        medicine = _locked_medicine(pk)
        if not medicine.is_active:
            raise ValidationError({"detail": "This medicine is already disabled."})
        medicine.is_active = False
        medicine.save(update_fields=["is_active"])
        _log(user, "MEDICINE_DISABLE", f"id={medicine.pk} name={medicine.name}")
    return medicine


def add_stock(user, pk, quantity):
    """FR-PHM-06: positive whole number, row locked, one transaction."""
    _require_pharmacist(user)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValidationError({"quantity": ["Quantity must be a whole number greater than zero."]})
    with transaction.atomic():
        medicine = _locked_medicine(pk)
        if not medicine.is_active:
            raise ValidationError({"detail": "This medicine is disabled. Stock cannot be added."})
        medicine.stock_left += quantity
        medicine.save(update_fields=["stock_left"])
        _log(user, "MEDICINE_STOCK_ADD", f"id={medicine.pk} added={quantity} stock_now={medicine.stock_left}")
    return medicine


def issue_line(user, pk):
    """FR-PHM-08/09: issue one PENDING line, lock the medicine, never go below zero."""
    _require_pharmacist(user)
    with transaction.atomic():
        try:
            line = PrescriptionMedicine.objects.select_for_update().get(pk=pk)
        except PrescriptionMedicine.DoesNotExist:
            raise NotFound("Prescription medicine line not found.")
        if line.status != PENDING:
            raise ValidationError({"detail": "This line has already been issued."})

        medicine = _locked_medicine(line.medicine_id)
        if not medicine.is_active:
            raise ValidationError({"detail": "This medicine is disabled and cannot be issued."})
        if medicine.stock_left < line.quantity_alloted:
            raise ValidationError(
                {
                    "detail": "Not enough stock. Add stock first.",
                    "available_stock": medicine.stock_left,
                    "required_quantity": line.quantity_alloted,
                }
            )

        medicine.stock_left -= line.quantity_alloted
        medicine.save(update_fields=["stock_left"])
        # unit_price and total stay as copied by the doctor when the prescription was saved (A11).
        line.status = ISSUED
        line.save(update_fields=["status"])
        _log(
            user,
            "MEDICINE_ISSUE",
            f"line={line.pk} prescription={line.prescription_id} medicine={medicine.pk} qty={line.quantity_alloted}",
        )
    return line
