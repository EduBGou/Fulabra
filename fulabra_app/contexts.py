from dataclasses import dataclass
from typing import List

from fulabra_app.forms import GameWordForm
from .models import (
    GamePlayer,
    GameRound,
    LobbyGroup,
    LobbyPlayer,
    Player,
    SubmittedWord,
    User,
    Word,
)

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


@dataclass
class GameFrameContext:
    lobby: LobbyGroup
    round: GameRound
    form: GameWordForm

    @property
    def available_words(self) -> List[Word]:
        return Word.objects.all()


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
