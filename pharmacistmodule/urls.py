from django.urls import path,include
from rest_framework.routers import DefaultRouter


#routing
router = DefaultRouter()


urlpatterns = [
    #root
    path('',include(router.urls)), 
]