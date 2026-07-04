from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from fulabra import settings
from .models import LobbyGroup, Player


def hx_redirect(viewname: str, kwargs: dict = None):
    response = HttpResponse()
    response["HX-Redirect"] = (
        reverse(viewname, kwargs=kwargs) if kwargs else reverse(viewname)
    )
    return response


def set_player_preset_avatar(
    request: HttpRequest, player: Player, preset: str
) -> Player:
    if preset and not request.FILES.get("avatar"):
        player.avatar = (
            "avatars/default_avatar.png"
            if preset == "default_avatar.png"
            else f"avatars/{preset}"
        )
    return player.save()


def lobby_is_full(lobby: LobbyGroup, player: Player = None) -> bool:
    if player and lobby.lobby_memberships.filter(player=player).exists():
        return False
    return lobby.lobby_memberships.count() >= 3


def invite_to_lobby(lobby: LobbyGroup) -> str:
    path = reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
    base_url = settings.BACKEND_BASE_URL.rstrip("/")
    return f"{base_url}{path}"


def broadcast_user_status(user, status):
    if not user or not user.is_authenticated:
        return
        
    channel_layer = get_channel_layer()
    friends = user.friends.all()
    
    for friend in friends:
        friends_group = f"notifications_{friend.username}"
        async_to_sync(channel_layer.group_send)(
            friends_group,
            {
                "type": "send_status_update",
                "friend_username": user.username,
                "status": status
            }
        )
