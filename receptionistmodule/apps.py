from django.apps import AppConfig


# Django app configuration for the receptionist workflow.
# This module is responsible for patient registration, bookings, and billing.
class ReceptionistmoduleConfig(AppConfig):
    """Application settings for the receptionist module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'receptionistmodule'
