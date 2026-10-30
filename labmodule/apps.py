from django.apps import AppConfig


# Django app configuration for the lab module.
# This app handles lab test requests and result submission flows.
class LabmoduleConfig(AppConfig):
    """Application settings for the lab module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'labmodule'
