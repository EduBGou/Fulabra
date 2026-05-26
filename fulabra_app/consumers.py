import threading
from channels.generic.websocket import WebsocketConsumer
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync
from .contexts import LobbyScreenContext

from .models import *


class LobbyConsumer(WebsocketConsumer):

    def connect(self):
        self.user: User = self.scope["user"]
        self.lobby_code: str = self.scope["url_route"]["kwargs"]["lobby_code"]
        self.lobby = LobbyGroup.objects.filter(code=self.lobby_code).first()

        self.accept()

        if (
            self.user.is_authenticated
            and self.lobby
            and self.lobby.memberships.count() <= 3
        ):
            async_to_sync(self.channel_layer.group_add)(
                self.lobby_code, self.channel_name
            )

            self.lobby_player_membership = LobbyPlayer.objects.filter(
                lobby=self.lobby, user=self.user
            ).first()

            if not self.lobby_player_membership:
                self.lobby_player_membership = LobbyPlayer.objects.create(
                    lobby=self.lobby, user=self.user
                )
            event = {"type": self.lobby_update_current_players.__name__}
            async_to_sync(self.channel_layer.group_send)(self.lobby_code, event)
        else:
            context = {
                "error_message": f"This lobby ins't avaliable for you.",
            }
            html = render_to_string(
                "fulabra_app/partials/error_message.html", {"context": context}
            )
            self.send(text_data=html)
            self.close()

    def disconnect(self, code):

        def delayed_lobby_cleanup(lobby_code: str):
            from .models import LobbyGroup

            fresh_lobby = LobbyGroup.objects.filter(code=lobby_code).first()
            if fresh_lobby and fresh_lobby.memberships.count() == 0:
                fresh_lobby.delete()
                print(f"Lobby {lobby_code} stayed empty and was deleted by timer.")

        async_to_sync(self.channel_layer.group_discard)(
            self.lobby_code, self.channel_name
        )

        if self.lobby_player_membership:
            LobbyPlayer.objects.filter(id=self.lobby_player_membership.id).delete()

        if self.lobby.memberships.count() == 0:
            cleanup_timer = threading.Timer(
                30.0,
                delayed_lobby_cleanup,
                args=[self.lobby_code],
            )
            cleanup_timer.start()
        else:
            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code,
                {"type": self.lobby_update_current_players.__name__},
            )

    def lobby_update_current_players(self, event):
        if self.lobby_player_membership:
            try:
                self.lobby_player_membership.refresh_from_db()
            except LobbyPlayer.DoesNotExist:
                return

        self.lobby.refresh_from_db()
        context = LobbyScreenContext(self.lobby_player_membership)
        html = render_to_string(
            "fulabra_app/partials/player_list.html", {"context": context}
        )

        self.send(text_data=html)

    def receive(self, text_data=None, bytes_data=None):
        import json

        data = json.loads(text_data)

        if data.get("action") == "start_game":
            self.lobby.refresh_from_db()
            self.lobby.status = LobbyGroup.LobbyStatus.STARTING
            self.lobby.save()
            threading.Thread(target=self.run_countdown).start()

    def run_countdown(self):
        import time

        for seconds_left in range(5, 0, -1):
            context = {"seconds": seconds_left}
            html_snippet = render_to_string(
                "fulabra_app/partials/countdown.html", {"context": context}
            )

            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code,
                {"type": self.broadcast_html.__name__, "html": html_snippet},
            )
            time.sleep(1)

        self.lobby.status = LobbyGroup.LobbyStatus.PLAYING
        self.lobby.save()

        context = {"lobby": self.lobby}
        html = render_to_string(
            "fulabra_app/partials/game_board.html", {"context": context}
        )

        async_to_sync(self.channel_layer.group_send)(
            self.lobby_code,
            {"type": self.broadcast_html.__name__, "html": html},
        )

    def broadcast_html(self, event):
        self.send(text_data=event["html"])
