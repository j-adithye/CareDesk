from rest_framework.routers import DefaultRouter

from .views import MedicineViewSet, PrescriptionLineViewSet

# Pharmacist routes are grouped around medicine inventory and prescription issue actions.
router = DefaultRouter()
router.register(r"medicines", MedicineViewSet, basename="pharmacist-medicine")
router.register(r"prescription-medicines", PrescriptionLineViewSet, basename="pharmacist-line")

urlpatterns = router.urls
