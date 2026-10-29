from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import DoctorAppointmentsView, PrescriptionView

#routing
router = DefaultRouter()



urlpatterns = [
    path(
        '<int:doctorid>/appointments/',
        DoctorAppointmentsView.as_view(),
        name='doctor-appointments'),
    path(
        '<int:doctorid>/appointments/<int:appointmentid>/prescription/',
        PrescriptionView.as_view(),
        name='write-prescription'
    ),
    
    #root
    path('',include(router.urls)), 
]