from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from fulabra_app.models import Player


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
