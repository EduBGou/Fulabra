import threading
import time
from channels.generic.websocket import WebsocketConsumer
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync

from .models import *


class LobbyConsumer(WebsocketConsumer):

    def connect(self):
        self.user: User = self.scope["user"]
        self.lobby_code = self.scope["url_route"]["kwargs"]["lobby_code"]
        try:
            self.lobby: LobbyGroup = LobbyGroup.objects.get(code=self.lobby_code)
        except:
            print("WS - lobby code don't match")

        self.accept()
        if self.user.is_authenticated and self.lobby.players.count() <= 3:
            async_to_sync(self.channel_layer.group_add)(
                self.lobby_code, self.channel_name
            )
            self.user.current_lobby = self.lobby
            self.user.save()
            event = {"type": self.lobby_update_current_players.__name__}
            async_to_sync(self.channel_layer.group_send)(self.lobby_code, event)
        else:
            context = {
                "error_message": f"YOU CANNOT ENTER IN THIS LOBBY: It is full or the player is not logged in.",
                "current_lobby": self.lobby,
                "players": self.lobby.players.all(),
                "user": self.scope["user"],
            }
            html = render_to_string(
                "fulabra_app/partials/error_message.html", context=context
            )
            print(f"DEBUG: Context data is -> {self.lobby}")
            self.send(text_data=html)
            self.close()

    def disconnect(self, code):

        async_to_sync(self.channel_layer.group_discard)(
            self.lobby_code, self.channel_name
        )

        if self.user.is_authenticated:
            self.user.current_lobby = None
            self.user.save()

        def delayed_lobby_cleanup(lobby_id, lobby_code_str):
            from .models import LobbyGroup

            try:
                lobby_instance = LobbyGroup.objects.get(id=lobby_id)

                if lobby_instance.players.count() == 0:
                    lobby_instance.delete()
                    print(
                        f"Lobby {lobby_code_str} stayed empty and was deleted by timer."
                    )
            except LobbyGroup.DoesNotExist:
                pass

        if self.lobby.players.count() == 0:
            delay_seconds = 30.0

            cleanup_timer = threading.Timer(
                delay_seconds,
                delayed_lobby_cleanup,
                args=[self.lobby.id, self.lobby_code],
            )
            cleanup_timer.start()
        else:
            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code, {"type": self.lobby_update_current_players.__name__}
            )

    def lobby_update_current_players(self, event):
        self.lobby.refresh_from_db()
        context = {
            "current_lobby": self.lobby,
            "players": self.lobby.players.all(),
            "user": self.scope["user"],
        }
        html = render_to_string(
            "fulabra_app/partials/player_list.html", context=context
        )

        self.send(text_data=html)

    def receive(self, text_data=None, bytes_data=None):
        import json

        data = json.loads(text_data)

        if data.get("action") == "start_game":
            self.lobby.status = "starting"
            self.lobby.save()
            # threading.Thread(target=self.run_countdown).start()

        for seconds_left in range(5, 0, -1):

            html_snippet = render_to_string(
                "fulabra_app/partials/countdown.html", {"seconds": seconds_left}
            )

            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code,
                {"type": self.broadcast_html.__name__, "html": html_snippet},
            )

            time.sleep(1)

            self.lobby.status = "playing"
            self.lobby.save()

            game_board_html = render_to_string(
                "fulabra_app/partials/game_board.html", {"lobby": self.lobby}
            )

            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code,
                {"type": self.broadcast_html.__name__, "html": game_board_html},
            )

    def broadcast_html(self, event):
        self.send(text_data=event["html"])

    # def run_countdown(self):
    #     """This method runs independently in the background"""
    #     from django.template.loader import render_to_string
    #     import time

    #     for seconds_left in range(5, 0, -1):
    #         html_snippet = render_to_string(
    #             "partials/countdown.html", {"seconds": seconds_left}
    #         )

    #         async_to_sync(self.channel_layer.group_send)(
    #             self.lobby_code, {"type": "timer_broadcast", "html": html_snippet}
    #         )
    #         time.sleep(1)
