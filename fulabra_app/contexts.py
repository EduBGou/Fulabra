from django.core.cache import cache

from dataclasses import dataclass
from typing import List

from fulabra_app.forms import GameWordForm
from .models import *


@dataclass
class RegisterContext:
    username_val: str
    email_val: str
    confirm_val: str
    error_message: str = None
    error: str = None


@dataclass
class PlayerListContext:

    lobby_player_membership: LobbyPlayer
    error_message: str = None

    @property
    def lobby_players(self) -> List[Player]:
        return [
            member.player
            for member in self.lobby_player_membership.lobby.lobby_memberships.all()
        ]

    @property
    def lobby_leader(self) -> Player:
        return self.lobby_player_membership.lobby.leader

    @property
    def players_count(self) -> int:
        return self.lobby_player_membership.lobby.lobby_memberships.count()

    @property
    def user_is_leader(self) -> bool:
        return self.lobby_leader == self.lobby_player_membership.player

    @property
    def can_start_game(self) -> bool:
        return self.lobby_is_full and self.user_is_leader

    @property
    def lobby_is_full(self) -> bool:
        return self.players_count == 3


@dataclass
class LobbyContext:
    current_lobby: LobbyGroup
    player: Player
    invite: str
    error_message: str = None

    def current_category(self) -> Category:
        return Category.objects.first()

    @property
    def categories(self) -> List[Category]:
        return Category.objects.all()

    @property
    def online_friends(self) -> list[User]:
        if not self.player.user:
            return []
        
        friends = self.player.user.friends.all()
        return [friend for friend in friends if cache.get(f"user_online_{friend.id}") == "online"]
    
    @property
    def lobby_players(self) -> list[Player]:
        return [member.player for member in self.current_lobby.lobby_memberships.all()]
    
    @property
    def pending_invite_user_ids(self) -> list[int]:
        from .models import Notification
        # Notificações não lidas enviadas da sala
        notes = Notification.objects.filter(
            sender=self.player.user,
            notification_type="game_invite",
            target_id=self.current_lobby.id,
            is_read=False
        )

        return list(notes.values_list("recipient_id", flat=True))


@dataclass
class GameFrameContext:
    lobby: LobbyGroup
    game: Game
    round: GameRound
    form: GameWordForm

    @property
    def available_words(self) -> List[Word]:
        return Word.objects.filter(category=self.lobby.game.category).all()


@dataclass
class RoundResultContext:
    submissions: SubmittedWord

    @property
    def round_result_list(self) -> List[RoundResultElement]:
        list: List[RoundResultElement] = []

        for sub in self.submissions:
            game_player = GamePlayer.objects.filter(
                game=sub.round.game, player=sub.player
            ).first()
            if game_player:
                list.append(RoundResultElement(sub.player, sub.word, game_player.score))
            else:
                print(
                    f"GamePlayer with player={sub.player.nickname} and game.id={sub.round.game.id} there is not exits!"
                )

        return list


@dataclass
class RoundResultElement:
    player: Player
    word: Word
    score: int


@dataclass
class CategoryContext:
    current_category: Category

    @property
    def categories(self) -> List[Category]:
        return Category.objects.all()
