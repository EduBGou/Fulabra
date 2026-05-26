from dataclasses import dataclass
from typing import List
from .models import LobbyPlayer, User


@dataclass
class RegisterContext:
    username_val : str
    email_val : str
    confirm_val : str
    error_message : str = None
    error : str = None

@dataclass
class LobbyScreenContext:

    lobby_player_membership : LobbyPlayer
    error_message :str  = None

    @property
    def lobby_players(self) -> List[User]:
        return [member.user for member in self.lobby_player_membership.lobby.memberships.all()]

    @property
    def players_count(self) -> int:
        return self.lobby_player_membership.lobby.memberships.count()

    @property
    def user_is_leader(self) -> bool:
        return self.lobby_leader == self.lobby_player_membership.user

    @property
    def can_start_game(self) -> bool:
        return self.lobby_is_full and self.user_is_leader

    @property
    def lobby_is_full(self) -> bool:
        return self.players_count == 3

    @property
    def lobby_leader(self) -> User:
        return self.lobby_player_membership.lobby.leader
