from django.apps import AppConfig


# Django app configuration for the doctor workflow.
# This keeps doctor-specific endpoints and logic grouped under one app label.
class DoctormoduleConfig(AppConfig):
    """Application settings for the doctor module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'doctormodule'
