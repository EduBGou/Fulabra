from channels.generic.websocket import WebsocketConsumer
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
# from django.urls import reverse
from .models import *


class LobbyConsumer(WebsocketConsumer):

    def connect(self):
        self.user: User = self.scope["user"]
        self.lobby_code = self.scope["url_route"]["kwargs"]["lobby_code"]
        self.lobby: LobbyGroup = get_object_or_404(LobbyGroup, code=self.lobby_code)

        self.accept()
        if self.user.is_authenticated and self.lobby.players.count() <= 3:
            async_to_sync(self.channel_layer.group_add)(
                self.lobby_code, self.channel_name
            )
            self.user.current_lobby = self.lobby
            self.user.save()
            event = {"type": self.lobby_update.__name__}
            async_to_sync(self.channel_layer.group_send)(self.lobby_code, event)
        else:
            context = {
                "error_message": f"YOU CANNOT ENTER IN THIS LOBBY: It is full or the player is not logged in.",
                "lobby_code": self.lobby.code,
                "players": self.lobby.players.all(),
                "user": self.scope["user"],
            }
            html = render_to_string(
                "fulabra_app/partials/error_message.html", context=context
            )
            self.send(text_data=html)
            self.close()

    def disconnect(self, code):

        async_to_sync(self.channel_layer.group_discard)(
            self.lobby_code, self.channel_name
        )

        if self.user.is_authenticated:
            self.user.current_lobby = None
            self.user.save()

        event = {"type": self.lobby_update.__name__}
        async_to_sync(self.channel_layer.group_send)(self.lobby_code, event)

    def lobby_update(self, event):
        context = {
            "lobby_code": self.lobby.code,
            "players": self.lobby.players.all(),
            "user": self.scope["user"],
        }
        html = render_to_string(
            "fulabra_app/partials/player_list.html", context=context
        )

        self.send(text_data=html)
