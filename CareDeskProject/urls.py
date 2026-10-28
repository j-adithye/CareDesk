"""
URL configuration for CareDeskProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin           # Django's built-in admin site
from django.urls import path, include      # path = one URL rule, include = hand over to another urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
                                           # ready-made login and token-refresh views

urlpatterns = [                            # Django checks these rules from top to bottom
    path('admin/', admin.site.urls),       # /admin/ opens Django's admin site

    path('api/auth/login/', TokenObtainPairView.as_view()),
    # POST username + password -> returns an "access" and a "refresh" token.
    # .as_view() turns the class into a function Django can call

    path('api/auth/refresh/', TokenRefreshView.as_view()),
    # POST a refresh token -> returns a new access token

    path('api/admin/', include('adminmodule.urls')),            # everything under /api/admin/ goes to the admin app
    path('api/doctor/', include('doctormodule.urls')),          # same idea for each module
    path('api/lab/', include('labmodule.urls')),
    path('api/receptionist/', include('receptionistmodule.urls')),
    # The trailing "/" matters. Without it the URL becomes /api/receptionistpatients/
    path('api/pharmacist/', include('pharmacistmodule.urls')),
]
