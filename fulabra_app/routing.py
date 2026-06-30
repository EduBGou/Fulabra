from django.urls import path

from .consumers import *

websocket_urlpatterns = [
    path("ws/lobby/<lobby_code>/", LobbyConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
