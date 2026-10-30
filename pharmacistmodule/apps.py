from django.apps import AppConfig


# Django app configuration for the pharmacist workflow.
# This module contains the medication inventory and prescription issue logic.
class PharmacistmoduleConfig(AppConfig):
    """Application settings for the pharmacist module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pharmacistmodule'
