from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .models import Staff
from .views import StaffViewset

#routing
router = DefaultRouter()
router.register('staffs',StaffViewset, basename='staff')


urlpatterns = [
    #root
    path('',include(router.urls))    
]