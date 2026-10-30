from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffViewset, DoctorViewset, AppointmentViewset


# Router for the admin API so the app can expose list/create/update endpoints
# without manually defining each route.
router = DefaultRouter()
router.register('staffs', StaffViewset, basename='staff')
router.register('doctors', DoctorViewset, basename='doctors')
router.register('appointments', AppointmentViewset, basename='appointments')


urlpatterns = [
    # Include all router-generated admin routes at the app root.
    path('', include(router.urls)),
]
