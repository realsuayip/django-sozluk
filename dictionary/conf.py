# Notice: Dictionary settings are located in apps.py

from django.apps import apps

__all__ = ["settings"]

settings = apps.get_app_config("dictionary")
