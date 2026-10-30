
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LabRequestViewSet, LabResultViewSet


router = DefaultRouter()

router.register(
    "requests",
    LabRequestViewSet,
    basename="lab-requests"
)

router.register(
    "results",
    LabResultViewSet,
    basename="lab-results"
)

urlpatterns = [
    path("", include(router.urls)),
]
