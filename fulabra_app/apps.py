from django.apps import AppConfig

class FulabraappConfig(AppConfig):
    name = "fulabra_app"

    def ready(self):
        from .models import LobbyPlayer, LobbyGroup
        import fulabra_app.signals

        try:
            LobbyPlayer.objects.all().delete()
            LobbyGroup.objects.all().delete()
            print("Server started: Cleared all stale lobby assignments.")
        except Exception:
            print("Server started: Failed to clear all stale lobby assignments.")
