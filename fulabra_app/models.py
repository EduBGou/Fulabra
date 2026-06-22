from random import choices
from django.db import models
from django.db.models import QuerySet
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

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
    def lobby_membership(self) -> LobbyPlayer:
        return getattr(self, Player.lobby_membership.__name__).first()

    @property
    def game_membership(self) -> GamePlayer:
        return getattr(self, Player.game_membership.__name__).first()

    @property
    def submitted_words(self) -> QuerySet[SubmittedWord]:
        return getattr(self, Player.submitted_words.__name__).first()

    def __str__(self):
        return f"{self.nickname}"


class LobbyGroup(models.Model):

    class LobbyStatus(models.TextChoices):
        WAITING = "waiting", _("Waiting for Players")
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
    def lobby_memberships(self) -> QuerySet[LobbyPlayer]:
        return getattr(self, LobbyGroup.lobby_memberships.__name__).all()

    @property
    def game(self) -> Game:
        return getattr(self, LobbyGroup.game.__name__).all()

    def generate_unique_code(self) -> str:
        """Helper method to generate a unique lobby code"""
        return "AAAAAA"
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
        related_name=LobbyGroup.lobby_memberships.__name__,
    )
    player = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        related_name=Player.lobby_membership.__name__,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player} is in {self.lobby}"


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


class Category(models.Model):
    name = models.CharField(max_length=64)

    @property
    def words(self) -> QuerySet[Word]:
        return getattr(self, Category.words.__name__).all()

    @property
    def games(self) -> QuerySet[Word]:
        return getattr(self, Category.games.__name__).all()

    def __str__(self):
        return f"{self.name}"


class Word(models.Model):
    label = models.CharField(max_length=40)
    category = models.ForeignKey(
        Category,
        related_name=Category.words.__name__,
        on_delete=models.CASCADE,
    )

    @property
    def submitts(self) -> QuerySet[SubmittedWord]:
        return getattr(self, Word.submitts.__name__).all()

    def __str__(self):
        return f"{self.label}"


class Game(models.Model):

    class GameStatus(models.TextChoices):
        START = "start", _("The game starts")
        CHOOSING = "choosing", _("Waiting for everyone to choose a word")
        RESULT = "round_result", _("Showing the round result")
        FINISHED = "finished", _("Game Over")

    def get_default_category():
        category, _ = Category.objects.get_or_create(name="Profissao")
        return category.id

    lobby = models.OneToOneField(
        LobbyGroup, related_name=LobbyGroup.game.__name__, on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20, choices=GameStatus.choices, default=GameStatus.START
    )

    category = models.ForeignKey(
        Category,
        related_name=Category.games.__name__,
        on_delete=models.CASCADE,
        default=get_default_category,
    )

    @property
    def game_memberships(self) -> QuerySet[GamePlayer]:
        return getattr(self, Game.game_memberships.__name__).all()

    @property
    def rounds(self) -> QuerySet[GameRound]:
        return getattr(self, Game.rounds.__name__).all()


class GameRound(models.Model):
    game = models.ForeignKey(
        Game, related_name=Game.rounds.__name__, on_delete=models.CASCADE
    )
    round_number = models.IntegerField()

    @property
    def submitted_words(self) -> QuerySet[SubmittedWord]:
        return getattr(self, GameRound.submitted_words.__name__).all()


class SubmittedWord(models.Model):
    round = models.ForeignKey(
        GameRound,
        related_name=GameRound.submitted_words.__name__,
        on_delete=models.CASCADE,
    )
    player = models.ForeignKey(
        Player, related_name=Player.submitted_words.__name__, on_delete=models.CASCADE
    )
    word = models.ForeignKey(
        Word, related_name=Word.submitts.__name__, on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("round", "player")


class GamePlayer(models.Model):
    game = models.ForeignKey(
        Game, related_name=Game.game_memberships.__name__, on_delete=models.CASCADE
    )
    player = models.OneToOneField(
        Player, related_name=Player.game_membership.__name__, on_delete=models.CASCADE
    )
    score = models.IntegerField(default=0)
