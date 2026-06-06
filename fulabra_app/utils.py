from django.http import HttpRequest, HttpResponse
from django.urls import reverse

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
    max_capacity = 3
    if player and lobby.memberships.filter(player=player).exists():
        return False
    return lobby.memberships.count() >= max_capacity


def invite_to_lobby(lobby: LobbyGroup) -> str:
    path = reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
    base_url = settings.BACKEND_BASE_URL.rstrip("/")
    return f"{base_url}{path}"

