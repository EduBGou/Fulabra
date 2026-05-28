from ast import List
from random import choices

from django.db import models
from django.db.models import QuerySet
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from fulabra import settings

characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
length = 6

CHARACTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LOBBY_CODE_LENGTH = 6


LOBBYPLAYER_LOBBY_RELATED_NAME = "memberships"


class User(AbstractUser):
    email = models.EmailField(("email address"), blank=True, unique=True)
    nickname = models.CharField(max_length=16, blank=True, null=True)
    avatar = models.ImageField(
        upload_to="avatars/", default="avatars/default_avatar.png"
    )
    wins = models.IntegerField(default=0)
    stars = models.IntegerField(default=0)

    friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    @property
    def leader_lobby(self) -> QuerySet[LobbyGroup]:
        return getattr(self, User.leader_lobby.__name__).all()

    @property
    def membership(self) -> QuerySet[LobbyPlayer]:
        return getattr(self, User.membership.__name__).all()

    def __str__(self):
        return f"{self.username}"


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
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=User.leader_lobby.__name__,
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

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lobby {self.code} ({self.status()})"


class LobbyPlayer(models.Model):
    lobby = models.ForeignKey(
        LobbyGroup,
        on_delete=models.CASCADE,
        related_name=LobbyGroup.memberships.__name__,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=User.membership.__name__,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} is in {self.lobby}"


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
