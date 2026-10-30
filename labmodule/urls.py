
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LabRequestViewSet, LabResultViewSet

# All lab endpoints are registered through a router to keep the URL design consistent.
router = DefaultRouter()

# Fetch pending or scheduled lab test requests for assigned patients.
router.register(
    "requests",
    LabRequestViewSet,
    basename="lab-requests"
)

# Store and retrieve lab test results submitted by technicians.
router.register(
    "results",
    LabResultViewSet,
    basename="lab-results"
)

urlpatterns = [
    path("", include(router.urls)),
]
