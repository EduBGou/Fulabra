from abc import ABC, abstractmethod

from django.http import HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from ..models import FriendRequest, LobbyGroup
from ..utils import hx_redirect


class NotificationStrategy(ABC):
    @abstractmethod
    def handle(self, request, notification, action):
        pass


class FriendRequestStrategy(NotificationStrategy):
    def handle(self, request, notification, action):
        friend_request = FriendRequest.objects.filter(id=notification.target_id).first()
        if friend_request:
            if action == "accept":
                friend_request.status = "accepted"
                request.user.friends.add(friend_request.from_user)
                friend_request.from_user.friends.add(request.user)

            elif action == "reject":
                friend_request.status = "rejected"

            friend_request.save()
        return None


class GameInviteStrategy(NotificationStrategy):
    def handle(self, request, notification, action):
        if action == "accept":
            lobby = LobbyGroup.objects.filter(id=notification.target_id).first()

            if lobby:
                return hx_redirect("lobby_invite", kwargs={"lobby_code": lobby.code})
            return HttpResponse("Lobby no longer exists", status=404)

        elif action == "reject":
            # Se o convite foi recusado, libera o botão de volta pra enviar convite
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"notifications_{notification.sender.username}",
                {"type": "trigger_sidebar_refresh"},
            )
        return None

_STRATEGIES = {
    "friend_request": FriendRequestStrategy(),
    "game_invite": GameInviteStrategy(),
}

class NotificationContext:
    def __init__(self, notification):
        self.notification = notification
        self.strategy = _STRATEGIES.get(notification.notification_type)

    def execute(self, request, action) -> HttpResponse | None:
        if not self.strategy:
            return None

        if not self.notification.is_read:
            self.notification.is_read = True
            self.notification.save()

        return self.strategy.handle(request, self.notification, action)