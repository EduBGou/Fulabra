import threading
from channels.generic.websocket import WebsocketConsumer
from django.template.loader import render_to_string
from django.contrib.sessions.backends.base import SessionBase
from asgiref.sync import async_to_sync
from .contexts import *
from .models import *


class LobbyConsumer(WebsocketConsumer):
    disconnect_timers: dict[str, threading.Timer] = {}

    def connect(self):
        self.user: User = self.scope["user"]
        self.session: SessionBase = self.scope.get("session", {})
        self.lobby_code: str = self.scope["url_route"]["kwargs"]["lobby_code"]
        self.lobby = LobbyGroup.objects.filter(code=self.lobby_code).first()
        self.lobby_player_membership: LobbyPlayer = None

        if not self.lobby:
            self.accept()
            self.send_error_message("This lobby doesn't exist.")
            self.close()
            return

        if self.user.is_authenticated:
            self.player = self.user.player
        else:
            guest_player_id = self.session.get("guest_player_id")
            self.player = (
                Player.objects.filter(id=guest_player_id).first()
                if guest_player_id
                else None
            )
        if not self.player:
            self.player = Player.objects.create(nickname="guest")
            self.session["guest_player_id"] = self.player.id
            self.session.save()

        timer_key = f"{self.lobby_code}_{self.player.id}"
        if timer_key in self.disconnect_timers:
            self.disconnect_timers[timer_key].cancel()
            del self.disconnect_timers[timer_key]

        current_player_count = self.lobby.memberships.count()
        self.lobby_player_membership = LobbyPlayer.objects.filter(
            lobby=self.lobby, player=self.player
        ).first()

        if not self.lobby_player_membership:
            if current_player_count >= 3:
                self.accept()
                self.send_error_message("This lobby is already full (max 3 players).")
                self.close()
                return

            LobbyPlayer.objects.filter(player=self.player).delete()
            self.lobby_player_membership = LobbyPlayer.objects.create(
                lobby=self.lobby, player=self.player
            )

        self.accept()
        async_to_sync(self.channel_layer.group_add)(self.lobby_code, self.channel_name)

        self.broadcast_player_list()

    def disconnect(self, code):

        async_to_sync(self.channel_layer.group_discard)(
            self.lobby_code, self.channel_name
        )

        if self.lobby_player_membership:
            timer_key = f"{self.lobby_code}_{self.player.id}"

            cleanup_timer = threading.Timer(
                10,
                self.player_cleanup,
                args=[self.lobby_code, self.lobby_player_membership.id, timer_key],
            )
            self.disconnect_timers[timer_key] = cleanup_timer
            cleanup_timer.start()

    def receive(self, text_data=None, bytes_data=None):
        import json

        data = json.loads(text_data)
        if data.get("action") == "start_game":
            self.lobby.refresh_from_db()
            if self.lobby.memberships.count() == 3 and self.lobby.leader == self.player:
                self.lobby.status = LobbyGroup.LobbyStatus.STARTING
                self.lobby.save()
            threading.Thread(target=self.run_countdown, daemon=True).start()
        elif data.get("action") == "cancel_match":
            self.lobby.refresh_from_db()
            if (
                self.lobby.leader == self.player
                and self.lobby.status == LobbyGroup.LobbyStatus.STARTING
            ):
                self.lobby.status = LobbyGroup.LobbyStatus.WAITING
                self.lobby.save()

                self.broadcast_player_list()

    def player_cleanup(self, lobby_code: str, membership_id: int, timer_key: str):
        if timer_key in self.disconnect_timers:
            del self.disconnect_timers[timer_key]

        memebership = LobbyPlayer.objects.filter(id=membership_id).first()
        memebership.delete()

        fresh_lobby = LobbyGroup.objects.filter(code=lobby_code).first()
        if not fresh_lobby:
            return

        if fresh_lobby.memberships.count() == 0:
            fresh_lobby.delete()
            print(f"Lobby {lobby_code} stayed empty and was deleted.")
        else:
            fresh_lobby.leader = (
                LobbyPlayer.objects.filter(lobby=fresh_lobby).first().player
            )
            fresh_lobby.save()
            self.broadcast_player_list()

    def run_countdown(self):
        import time

        for seconds_left in range(5, 0, -1):

            self.lobby.refresh_from_db()
            if self.lobby.status != LobbyGroup.LobbyStatus.STARTING:
                return

            context = {"seconds_left": seconds_left}
            html = render_to_string(
                "fulabra_app/partials/countdown.html", {"context": context}
            )

            async_to_sync(self.channel_layer.group_send)(
                self.lobby_code,
                {"type": self.broadcast_html.__name__, "html": html},
            )

            cancel_button_html = render_to_string(
                "fulabra_app/partials/cancel_button.html"
            )
            async_to_sync(self.channel_layer.send)(
                self.channel_name,
                {"type": self.broadcast_html.__name__, "html": cancel_button_html},
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

    def send_current_players(self, event):
        if self.lobby_player_membership:
            try:
                self.lobby_player_membership.refresh_from_db()
            except LobbyPlayer.DoesNotExist:
                return

        self.lobby.refresh_from_db()
        context = PlayerListContext(self.lobby_player_membership)
        html = render_to_string(
            "fulabra_app/partials/player_list.html", {"context": context}
        )

        self.send(text_data=html)

    def broadcast_html(self, event):
        self.send(text_data=event["html"])

    def broadcast_player_list(self):
        """Sends a signal to the entire group channel to refresh their lists."""
        async_to_sync(self.channel_layer.group_send)(
            self.lobby_code, {"type": self.send_current_players.__name__}
        )

    def send_error_message(self, message: str):
        """Utility helper to push immediate partial errors back to client interface."""
        context = {"error_message": message}
        html = render_to_string(
            "fulabra_app/partials/error_message.html", {"context": context}
        )
        self.send(text_data=html)
