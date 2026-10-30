from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import StaffViewset,DoctorViewset, AppointmentViewset


#routing
router = DefaultRouter()
router.register('staffs',StaffViewset, basename='staff')
router.register('doctors',DoctorViewset, basename='doctors')
router.register('appointments',AppointmentViewset, basename='appointments')



urlpatterns = [
    #root
    path('',include(router.urls)),
       
]
