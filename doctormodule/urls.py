from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DoctorAppointmentsView,
    PatientMedicineLogView,
    PrescriptionView,
    PatientTestReportsView,
    PatientNotesLogView,
)

# The doctor module exposes a small set of patient-focused endpoints.
# These routes support appointment lookup, prescription creation, and medical history retrieval.
router = DefaultRouter()

urlpatterns = [
    # Fetch medicines prescribed to a patient in a date range.
    path(
        "patient/<int:patientid>/medicines/",
        PatientMedicineLogView.as_view(),
        name="patient-medicine-log"
    ),
    # List appointments for a doctor on the current day.
    path(
        '<int:doctorid>/appointments/',
        DoctorAppointmentsView.as_view(),
        name='doctor-appointments'),
    # Create or fetch a prescription for a specific appointment.
    path(
        '<int:doctorid>/appointments/<int:appointmentid>/prescription/',
        PrescriptionView.as_view(),
        name='write-prescription'
    ),
    # Retrieve lab test results for a patient.
    path(
        "patient/<int:patientid>/tests/",
        PatientTestReportsView.as_view(),
        name="patient-test-reports"
    ),
    # Retrieve the notes log for a patient across appointments.
    path(
        'patient/<patientid>/log/',
        PatientNotesLogView.as_view(),
        name='doctor-appointments'),
    # Include router-generated paths if any are added later.
    path('', include(router.urls)),
]