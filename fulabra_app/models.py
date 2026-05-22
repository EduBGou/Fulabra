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

    nickname = models.CharField(max_length=16, blank=True, null=True)
    avatar = models.CharField(max_length=100, default='default_avatar.png')
    wins = models.IntegerField(default=0)
    stars = models.IntegerField(default=0)


class Match(models.Model):
    player1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='matches_as_p1'
    )
    
    player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='matches_as_p2'
    )

    player3 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='matches_as_p3'
    )

    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='matches_won'
    )

    date_played = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Partida {self.id} - Vencedor: {self.winner.username if self.winner else 'Empate'}"


class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pendente'),
        ('accepted', 'Aceito'),
        ('rejected', 'Recusado'),
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests'
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_friend_requests'
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"De {self.from_user.username} para {self.to_user.username} ({self.status})"


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
