from django.apps import AppConfig
from django.db.models.signals import post_migrate


class FulabraappConfig(AppConfig):
    name = "fulabra_app"

    def ready(self):
        from .models import LobbyPlayer, LobbyGroup

        try:
            LobbyPlayer.objects.all().delete()
            LobbyGroup.objects.all().delete()
            print("Server started: Cleared all stale lobby assignments.")
        except Exception:
            print("Server started: Failed to clear all stale lobby assignments.")
