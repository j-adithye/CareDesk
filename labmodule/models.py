

# Lab module model definitions.
# The main entity here is LabResult, which stores technician-submitted test outcomes.
from django.db import models
from adminmodule.models import Staff, PrescriptionTest


class LabResult(models.Model):
    """Stores a single test result and links it to the related prescription test."""

    prescription_test = models.OneToOneField(
        PrescriptionTest,
        on_delete=models.PROTECT,
        related_name="lab_result"
    )

    technician = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        related_name="lab_results"
    )

    result_value = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a readable identifier for the result record."""
        return f"Lab Result {self.pk}"
