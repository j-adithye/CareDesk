from django.apps import AppConfig


# Django app configuration for the admin module.
# This tells Django which application this config belongs to and which
# automatic primary key field to use for new models.
class AdminmoduleConfig(AppConfig):
    """Application settings for the admin role and shared domain models."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminmodule'
