from rest_framework.routers import DefaultRouter

from .views import MedicineViewSet, PrescriptionLineViewSet

router = DefaultRouter()
router.register(r"medicines", MedicineViewSet, basename="pharmacist-medicine")
router.register(r"prescription-medicines", PrescriptionLineViewSet, basename="pharmacist-line")

urlpatterns = router.urls
