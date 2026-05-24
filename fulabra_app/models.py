from random import choices

from django.db import models
from django.contrib.auth.models import AbstractUser


characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
length = 8

class LobbyGroup(models.Model):
    code = models.CharField(max_length=6, unique=True, blank=True)
    leader = models.OneToOneField(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leader_lobby",
    )

    def save(self, *args, **kwargs):
        if not self.code:
            while True:
                code = "".join(choices(characters, k=length))
                if not self.__class__.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class User(AbstractUser):
    email = models.EmailField(("email address"), blank=True, unique=True)
    current_lobby = models.ForeignKey(
        LobbyGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="players",
    )

    friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    def __str__(self):
        return f"{self.username}"
