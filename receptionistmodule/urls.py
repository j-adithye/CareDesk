from django.urls import path, include              # path = one rule, include = bring in other rules
from rest_framework.routers import DefaultRouter   # builds URLs automatically from a ViewSet
from .views import PatientViewSet, DoctorViewSet, AppointmentViewSet,BillingListView # Imports the patient, doctor, and appointment APIs.                # our view class (. means "this same folder")

router = DefaultRouter()                           # create an empty router

router.register("patients", PatientViewSet, basename="patient")
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("appointments", AppointmentViewSet, basename="appointment")
# Registers the appointment API endpoints.
# "patients"  -> the word in the URL:  /api/receptionist/patients/
# PatientViewSet -> the class that handles those URLs
# basename    -> an internal name Django uses to refer to these routes

urlpatterns = [
    path("", include(router.urls)), 
    path("bills/", BillingListView.as_view(), name="billing-list"),# add all the URLs the router created
]