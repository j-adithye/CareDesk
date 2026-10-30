from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import DoctorAppointmentsView, PatientMedicineLogView, PrescriptionView, PatientTestReportsView, PatientNotesLogView

#routing
router = DefaultRouter()



urlpatterns = [
    path(
        "patient/<int:patientid>/medicines/",
        PatientMedicineLogView.as_view(),
        name="patient-medicine-log"
    ),
    path(
        '<int:doctorid>/appointments/',
        DoctorAppointmentsView.as_view(),
        name='doctor-appointments'),
    path(
        '<int:doctorid>/appointments/<int:appointmentid>/prescription/',
        PrescriptionView.as_view(),
        name='write-prescription'
    ),
    path(
        "patient/<int:patientid>/tests/",
        PatientTestReportsView.as_view(),
        name="patient-test-reports"
    ),
    path(
        'patient/<patientid>/log/',
        PatientNotesLogView.as_view(),
        name='doctor-appointments'),
    #root
    path('',include(router.urls)), 
]