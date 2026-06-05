from random import choices

from django.db import models
from django.db.models import QuerySet
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from fulabra import settings

CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LOBBY_CODE_LENGTH = 6


class User(AbstractUser):
    email = models.EmailField(("email address"), blank=True, unique=True)

    wins = models.IntegerField(default=0)
    stars = models.IntegerField(default=0)
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    @property
    def player(self) -> Player:
        return getattr(self, User.player.__name__).first()


class Player(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name=User.player.__name__,
        null=True,
        blank=True,
    )

    nickname = models.CharField(max_length=16)
    avatar = models.ImageField(
        upload_to="avatars/", default="avatars/default_avatar.png"
    )

    @property
    def is_guest(self) -> bool:
        return self.user is None

    @property
    def leader_lobby(self) -> LobbyGroup:
        return getattr(self, Player.leader_lobby.__name__).first()

    @property
    def membership(self) -> LobbyPlayer:
        return getattr(self, Player.membership.__name__).first()

    def __str__(self):
        return f"{self.nickname}"


class LobbyGroup(models.Model):

    class LobbyStatus(models.TextChoices):
        WAITING = "waiting", _("Waiting for Players")
        STARTING = "starting", _("Starting Countdown")
        PLAYING = "playing", _("In Game")
        FINISHED = "finished", _("Game Over")

    code = models.CharField(
        max_length=LOBBY_CODE_LENGTH,
        unique=True,
        editable=False,
        db_index=True,
    )

    leader = models.OneToOneField(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=Player.leader_lobby.__name__,
    )

    status = models.CharField(
        max_length=20, choices=LobbyStatus.choices, default=LobbyStatus.WAITING
    )

    @property
    def memberships(self) -> QuerySet[LobbyPlayer]:
        return getattr(self, LobbyGroup.memberships.__name__).all()

    def generate_unique_code(self) -> str:
        """Helper method to generate a unique lobby code"""
        while True:
            new_code = "".join(choices(CHARACTERS, k=LOBBY_CODE_LENGTH))
            if not LobbyGroup.objects.filter(code=new_code).exists():
                return new_code

    def __str__(self):
        return f"Lobby {self.code} ({self.status})"


class LobbyPlayer(models.Model):
    lobby = models.ForeignKey(
        LobbyGroup,
        on_delete=models.CASCADE,
        related_name=LobbyGroup.memberships.__name__,
    )
    player = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        related_name=Player.membership.__name__,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player} is in {self.lobby}"


class Match(models.Model):
    player1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches_as_p1"
    )

    player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches_as_p2"
    )

    player3 = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches_as_p3"
    )

    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="matches_won",
    )

    date_played = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Partida {self.id} - Vencedor: {self.winner.username if self.winner else 'Empate'}"


class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pendente"),
        ("accepted", "Aceito"),
        ("rejected", "Recusado"),
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"De {self.from_user.username} para {self.to_user.username} ({self.status})"
        )
