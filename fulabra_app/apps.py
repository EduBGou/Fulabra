from django.apps import AppConfig
from django.db.models.signals import post_migrate


class FulabraappConfig(AppConfig):
    name = "fulabra_app"

    def ready(self):
        from .models import User

        try:
            User.objects.filter(current_lobby__isnull=False).update(current_lobby=None)
            print("Server started: Cleared all stale lobby assignments.")
        except Exception:
            print("Server started: Failed to clear all stale lobby assignments.")
