from typing import List

from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.db.models import QuerySet
from fulabra import settings
from fulabra_app.contexts import RoundResultElement
from .models import Game, GameRound, LobbyGroup, Player, SubmittedWord, User, Word

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


def get_last_game_round(game) -> GameRound:
    GameRound.objects.filter(game=game).order_by("-round_number").first()


def perform_scoring(
    game: Game, submissions: List[SubmittedWord], perfom: bool = True
) -> List[RoundResultElement]:

    words = [sub.word for sub in submissions if sub.word]
    word_frequencies: dict[Word, int] = {}
    results: List[RoundResultElement] = []
    current_round = GameRound.objects.filter()

    for w in words:
        word_frequencies[w] = word_frequencies.get(w, 0) + 1

    inactive_players = [m.player for m in game.game_memberships.all()]

    for sub in submissions:
        inactive_players.remove(sub.player)
        game_player = sub.player.game_membership.filter(game=game).first()

        if word_frequencies[sub.word] == 2:
            game_player.score += 1 if perfom else 0
            game_player.save()
            results.append(
                RoundResultElement(sub.player, sub.word, game_player.score, "earns")
            )

        elif word_frequencies[sub.word] == 3 and game_player.score > 0:
            game_player.score -= 1 if perfom else 0
            game_player.save()
            results.append(
                RoundResultElement(sub.player, sub.word, game_player.score, "loses")
            )
        else:
            results.append(RoundResultElement(sub.player, sub.word, game_player.score))
    current_round = get_last_game_round(game)
    for p in inactive_players:
        score = p.game_membership.filter(game=game).first().score
        SubmittedWord.objects.create(round=current_round, player=p)
        results.append(RoundResultElement(p, None, score))

    return results


def get_submissions(current_round: GameRound) -> QuerySet[SubmittedWord]:
    return current_round.submitted_words.select_related("word", "player").all()


def invite_to_lobby(lobby: LobbyGroup) -> str:
    path = reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
    base_url = settings.BACKEND_BASE_URL.rstrip("/")
    return f"{base_url}{path}"


def broadcast_user_status(user: User, status):
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
                "status": status,
            },
        )
