from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import DoctorAppointmentsView

#routing
router = DefaultRouter()



urlpatterns = [
    path(
        '<int:doctorid>/appointments/',
        DoctorAppointmentsView.as_view(),
        name='doctor-appointments'),
    #root
    path('',include(router.urls)), 
]