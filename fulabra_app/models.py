from django.db import models
from django.contrib.auth.models import AbstractUser

from fulabra import settings


class LobbyGroup(models.Model):
    code = models.CharField(max_length=8)

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


# class Player(models.Model):
#     lobby = models.ForeignKey(
#         LobbyGroup, on_delete=models.CASCADE, related_name="players"
#     )

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
#     )

#     session_key = models.CharField(max_length=40, db_index=True)

#     nickname = models.CharField(max_length=50)

#     def __str__(self):
#         return self.nickname
