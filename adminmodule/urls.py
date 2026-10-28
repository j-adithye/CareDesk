from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import StaffViewset


#routing
router = DefaultRouter()
router.register('staffs',StaffViewset, basename='staff')



urlpatterns = [
    #root
    path('',include(router.urls)),
       
]